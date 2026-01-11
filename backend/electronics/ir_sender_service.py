import math
import tempfile
from typing import Any, Dict, Optional

from database import Database

from .ir_ctl_engine import IrCtlEngine
from .ir_signal_parser import IrSignalParser


class IrSenderService:
    def __init__(self, store: Database, engine: IrCtlEngine, parser: IrSignalParser) -> None:
        self._db = store
        self._engine = engine
        self._parser = parser

    def send(self, button_id: int, mode: str, hold_ms: Optional[int]) -> Dict[str, Any]:
        mode = mode.strip().lower()
        if mode not in ("press", "hold"):
            raise ValueError("mode must be 'press' or 'hold'")

        button = self._db.buttons.get(button_id)
        signals = self._db.signals.list_by_button(button_id)
        if not signals:
            raise ValueError("No signals for button")

        remote = self._db.remotes.get(int(button["remote_id"]))

        carrier_hz = int(remote["carrier_hz"]) if remote.get("carrier_hz") else None
        duty_cycle = int(remote["duty_cycle"]) if remote.get("duty_cycle") else None

        with tempfile.TemporaryDirectory(prefix="ir_tx_") as tmpdir:
            if mode == "press":
                press_initial = self._parser.decode_pulses(str(signals["press_initial"]))
                press_path = f"{tmpdir}/press_initial.txt"
                self._write_pulse_space_file(press_path, press_initial)

                stdout, stderr = self._engine.send_pulse_space_files(
                    [press_path],
                    carrier_hz=carrier_hz,
                    duty_cycle=duty_cycle,
                )

                return {
                    "button_id": button_id,
                    "mode": "press",
                    "carrier_hz": carrier_hz,
                    "duty_cycle": duty_cycle,
                    "gap_us": None,
                    "repeats": 0,
                    "stdout": stdout,
                    "stderr": stderr,
                }

            if hold_ms is None or int(hold_ms) <= 0:
                raise ValueError("hold_ms is required for mode=hold")

            hold_initial_text = str(signals.get("hold_initial") or "").strip()
            hold_repeat_text = str(signals.get("hold_repeat") or "").strip()
            if not hold_initial_text or not hold_repeat_text:
                raise ValueError("Hold signals are missing for this button")

            # Hold repeats require an explicit inter-frame gap because stored pulses end on a pulse.
            hold_gap_us = signals.get("hold_gap_us")
            if hold_gap_us is None or int(hold_gap_us) <= 0:
                raise ValueError("Hold gap is missing for this button; re-capture hold to compute it")
            hold_gap_us_value = int(hold_gap_us)

            hold_initial = self._parser.decode_pulses(hold_initial_text)
            hold_repeat = self._parser.decode_pulses(hold_repeat_text)

            initial_path = f"{tmpdir}/hold_initial.txt"
            repeat_path = f"{tmpdir}/hold_repeat.txt"
            self._write_pulse_space_file(initial_path, hold_initial)
            self._write_pulse_space_file(repeat_path, hold_repeat)

            repeat_count = self._estimate_repeat_count(
                hold_ms=int(hold_ms),
                initial_pulses=hold_initial,
                repeat_pulses=hold_repeat,
                gap_us=hold_gap_us_value,
            )

            file_paths = [initial_path] + [repeat_path] * repeat_count

            stdout, stderr = self._engine.send_pulse_space_files(
                file_paths,
                gap_us=hold_gap_us_value,
                carrier_hz=carrier_hz,
                duty_cycle=duty_cycle,
            )

            return {
                "button_id": button_id,
                "mode": "hold",
                "hold_ms": int(hold_ms),
                "carrier_hz": carrier_hz,
                "duty_cycle": duty_cycle,
                "gap_us": hold_gap_us_value,
                "repeats": repeat_count,
                "stdout": stdout,
                "stderr": stderr,
            }

    def _write_pulse_space_file(self, path: str, pulses: list[int]) -> None:
        text = self._parser.to_pulse_space_text(pulses)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def _estimate_repeat_count(self, hold_ms: int, initial_pulses: list[int], repeat_pulses: list[int], gap_us: Optional[int]) -> int:
        # This is only an estimate. The IR receiver usually tolerates small timing errors.
        target_us = int(hold_ms) * 1000

        initial_us = sum(abs(int(v)) for v in initial_pulses)
        repeat_us = sum(abs(int(v)) for v in repeat_pulses)

        repeat_period_us = repeat_us + (int(gap_us) if gap_us and gap_us > 0 else 0)

        remaining_us = max(0, target_us - initial_us)
        if repeat_period_us <= 0:
            return 1

        return max(1, int(math.ceil(remaining_us / float(repeat_period_us))))
