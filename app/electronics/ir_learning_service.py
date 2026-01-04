import re
import threading
import time
from typing import Any, Dict, List, Optional

from database import Database

from .ir_ctl_engine import IrCtlEngine
from .ir_hold_extractor import IrHoldExtractor
from .ir_signal_aggregator import IrSignalAggregator
from .ir_signal_parser import IrSignalParser
from .models import LearningSession, LogEntry


class IrLearningService:
    def __init__(
        self,
        database: Database,
        engine: IrCtlEngine,
        parser: IrSignalParser,
        aggregator: IrSignalAggregator,
        hold_extractor: IrHoldExtractor,
        debug: bool,
        aggregate_round_to_us: int,
        aggregate_min_match_ratio: float,
        hold_idle_timeout_ms: int,
    ) -> None:
        self._db = database
        self._engine = engine
        self._parser = parser
        self._aggregator = aggregator
        self._hold_extractor = hold_extractor
        self._debug = debug

        self._aggregate_round_to_us = aggregate_round_to_us
        self._aggregate_min_match_ratio = aggregate_min_match_ratio
        self._hold_idle_timeout_ms = hold_idle_timeout_ms

        self._lock = threading.Lock()
        self._session: Optional[LearningSession] = None

    @property
    def is_learning(self) -> bool:
        with self._lock:
            return self._session is not None

    @property
    def remote_id(self) -> Optional[int]:
        with self._lock:
            return self._session.remote_id if self._session else None

    @property
    def remote_name(self) -> Optional[str]:
        with self._lock:
            return self._session.remote_name if self._session else None

    def start(self, remote_id: int, extend: bool) -> Dict[str, Any]:
        with self._lock:
            if self._session is not None:
                raise RuntimeError("Learning session is already running")

        remote = self._db.remotes.get(remote_id)

        if not extend:
            self._db.remotes.clear_buttons(remote_id)

        next_index = 1
        if extend:
            next_index = self._compute_next_button_index(remote_id)

        session = LearningSession(
            remote_id=remote_id,
            remote_name=str(remote["name"]),
            extend=bool(extend),
            started_at=time.time(),
            next_button_index=next_index,
        )
        self._log(session, "info", "Learning session started", {"remote_id": remote_id, "extend": bool(extend)})

        with self._lock:
            self._session = session

        return self.status()

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            session = self._session
            self._session = None

        if session:
            self._log(session, "info", "Learning session stopped")
            return self._session_to_dict(session, active=False)

        return {"learn_enabled": False}

    def capture(
        self,
        remote_id: int,
        mode: str,
        takes: int,
        timeout_ms: int,
        overwrite: bool,
        button_name: Optional[str],
    ) -> Dict[str, Any]:
        mode = mode.strip().lower()
        if mode not in ("press", "hold"):
            raise ValueError("mode must be 'press' or 'hold'")
        if takes <= 0:
            raise ValueError("takes must be > 0")
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be > 0")

        session = self._get_session_or_raise(remote_id)

        if mode == "press":
            return self._capture_press(session, takes=takes, timeout_ms=timeout_ms, overwrite=overwrite, button_name=button_name)

        return self._capture_hold(session, timeout_ms=timeout_ms, overwrite=overwrite, button_name=button_name)

    def status(self) -> Dict[str, Any]:
        with self._lock:
            session = self._session

        if not session:
            return {"learn_enabled": False}

        return self._session_to_dict(session, active=True)

    # -----------------------------
    # Internal
    # -----------------------------

    def _get_session_or_raise(self, remote_id: int) -> LearningSession:
        with self._lock:
            session = self._session

        if not session:
            raise RuntimeError("Learning session is not running")
        if int(session.remote_id) != int(remote_id):
            raise RuntimeError("Learning session is running for a different remote")
        return session

    def _capture_press(
        self,
        session: LearningSession,
        takes: int,
        timeout_ms: int,
        overwrite: bool,
        button_name: Optional[str],
    ) -> Dict[str, Any]:
        name = self._resolve_press_button_name(session, button_name)
        auto_generated = not (button_name and button_name.strip())


        existing_button = self._db.buttons.get_by_name(session.remote_id, name)
        existing_signals = self._db.signals.list_by_button(int(existing_button["id"])) if existing_button else None
        if existing_signals and not overwrite:
            raise RuntimeError("Press signal already exists (set overwrite=true to replace)")

        raw_lines: List[str] = []
        frames: List[List[int]] = []
        tail_gaps: List[Optional[int]] = []

        self._log(session, "info", "Capture press started", {"button_name": name, "takes": takes})

        for i in range(takes):
            self._log(session, "info", "Waiting for IR press", {"take": i + 1, "timeout_ms": timeout_ms})
            raw, stdout, stderr = self._engine.receive_one_message(timeout_ms=timeout_ms)
            if stdout or stderr:
                self._log(session, "debug", "ir-ctl output", {"stdout": stdout, "stderr": stderr})

            pulses, tail_gap_us = self._parser.parse_and_normalize(raw)

            raw_lines.append(raw)
            frames.append(pulses)
            tail_gaps.append(tail_gap_us)

            self._log(
                session,
                "info",
                "Captured press take",
                {"take": i + 1, "pulses": len(pulses), "tail_gap_us": tail_gap_us},
            )

        aggregated, used_indices, score = self._aggregator.aggregate(
            frames,
            round_to_us=self._aggregate_round_to_us,
            min_match_ratio=self._aggregate_min_match_ratio,
        )

        press_initial = self._parser.encode_pulses(aggregated)

        # Update remote gap default if we can infer it from the successful takes.        
        gap_candidates: list[int] = []
        for idx in used_indices:
            if idx >= len(tail_gaps):
                continue
            gap = tail_gaps[idx]
            if gap is None or gap <= 0:
                continue
            gap_candidates.append(gap)
            
        if gap_candidates:
            gap_us = self._median_int(gap_candidates)
            self._db.remotes.update_gap_default_if_empty(session.remote_id, gap_us_default=gap_us)

        # Persist only after capture succeeded.
        button = existing_button
        if not button:
            button = self._db.buttons.create(remote_id=session.remote_id, name=name)
            if auto_generated:
                session.next_button_index += 1

        button_id = int(button["id"])

        if self._debug:
            for take_idx, raw in enumerate(raw_lines):
                self._db.captures.create(button_id=button_id, mode="press", take_index=take_idx, raw_text=raw)

        signals = self._db.signals.upsert_press(
            button_id=button_id,
            press_initial=press_initial,
            press_repeat=None,
            sample_count_press=len(used_indices),
            quality_score_press=score,
            encoding="signed_us_v1",
        )

        session.last_button_id = button_id
        session.last_button_name = str(button["name"])

        self._log(session, "info", "Capture press finished", {"button_id": button_id, "quality": score})

        return {
            "remote_id": session.remote_id,
            "button": button,
            "signals": signals,
        }

    def _capture_hold(
        self,
        session: LearningSession,
        timeout_ms: int,
        overwrite: bool,
        button_name: Optional[str],
    ) -> Dict[str, Any]:
        button = self._resolve_hold_button(session, button_name)
        button_id = int(button["id"])

        signals = self._db.signals.list_by_button(button_id)
        if not signals:
            raise ValueError("Press must be captured before hold can be captured")

        has_hold = bool(str(signals.get("hold_initial") or "").strip())
        if has_hold and not overwrite:
            raise RuntimeError("Hold signal already exists (set overwrite=true to replace)")

        self._log(session, "info", "Capture hold started", {"button_id": button_id, "timeout_ms": timeout_ms})

        frames_raw: List[str] = []
        frames: List[List[int]] = []

        deadline = time.time() + (timeout_ms / 1000.0)

        # First message (initial)
        self._log(session, "info", "Waiting for IR hold (initial frame)", {"timeout_ms": timeout_ms})
        first_raw, stdout, stderr = self._engine.receive_one_message(timeout_ms=timeout_ms)
        if stdout or stderr:
            self._log(session, "debug", "ir-ctl output", {"stdout": stdout, "stderr": stderr})
        first_pulses, _ = self._parser.parse_and_normalize(first_raw)
        frames_raw.append(first_raw)
        frames.append(first_pulses)

        # Subsequent messages (repeats) until idle.
        while True:
            remaining_ms = int(max(0.0, (deadline - time.time()) * 1000.0))
            if remaining_ms <= 0:
                break

            per_call_timeout_ms = min(self._hold_idle_timeout_ms, remaining_ms)

            try:
                raw, _, _ = self._engine.receive_one_message(timeout_ms=per_call_timeout_ms)
            except TimeoutError:
                break

            pulses, _ = self._parser.parse_and_normalize(raw)
            frames_raw.append(raw)
            frames.append(pulses)

        if len(frames) < 2:
            raise ValueError("Hold capture needs at least 2 frames. Hold the button longer or increase timeout_ms.")

        hold_initial, hold_repeat, repeat_count, repeat_score = self._hold_extractor.extract(
            frames,
            round_to_us=self._aggregate_round_to_us,
            min_match_ratio=self._aggregate_min_match_ratio,
        )

        if hold_repeat is None:
            raise ValueError("Failed to extract a repeat frame from the hold capture")

        hold_initial_text = self._parser.encode_pulses(hold_initial)
        hold_repeat_text = self._parser.encode_pulses(hold_repeat)

        if self._debug:
            for idx, raw in enumerate(frames_raw):
                self._db.captures.create(button_id=button_id, mode="hold", take_index=idx, raw_text=raw)

        updated = self._db.signals.update_hold(
            button_id=button_id,
            hold_initial=hold_initial_text,
            hold_repeat=hold_repeat_text,
            sample_count_hold=len(frames),
            quality_score_hold=repeat_score,
        )

        session.last_button_id = button_id
        session.last_button_name = str(button["name"])

        self._log(
            session,
            "info",
            "Capture hold finished",
            {"button_id": button_id, "repeat_frames": repeat_count, "quality": repeat_score},
        )

        return {
            "remote_id": session.remote_id,
            "button": button,
            "signals": updated,
        }

    def _resolve_press_button_name(self, session: LearningSession, button_name: Optional[str]) -> str:
        if button_name and button_name.strip():
            return button_name.strip()
        return f"BTN_{session.next_button_index:04d}"

    def _resolve_hold_button(self, session: LearningSession, button_name: Optional[str]) -> Dict[str, Any]:
        if button_name and button_name.strip():
            button = self._db.buttons.get_by_name(session.remote_id, button_name.strip())
            if not button:
                raise ValueError("Unknown button name")
            return button

        if session.last_button_id is None:
            raise ValueError("button_name is required (no previous button in session)")

        button = self._db.buttons.get(session.last_button_id)
        if int(button["remote_id"]) != int(session.remote_id):
            raise RuntimeError("Last button belongs to a different remote")
        return button

    def _compute_next_button_index(self, remote_id: int) -> int:
        buttons = self._db.buttons.list(remote_id)
        best = 0
        for b in buttons:
            name = str(b.get("name") or "")
            m = re.match(r"^BTN_(\d{4})$", name)
            if not m:
                continue
            try:
                best = max(best, int(m.group(1)))
            except Exception:
                pass
        return best + 1 if best > 0 else 1

    def _log(self, session: LearningSession, level: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        session.logs.append(LogEntry(timestamp=time.time(), level=level, message=message, data=data))

    def _session_to_dict(self, session: LearningSession, active: bool) -> Dict[str, Any]:
        return {
            "learn_enabled": bool(active),
            "remote_id": session.remote_id,
            "remote_name": session.remote_name,
            "extend": bool(session.extend),
            "started_at": session.started_at,
            "last_button_id": session.last_button_id,
            "last_button_name": session.last_button_name,
            "next_button_index": session.next_button_index,
            "logs": [
                {
                    "timestamp": e.timestamp,
                    "level": e.level,
                    "message": e.message,
                    "data": e.data,
                }
                for e in session.logs
            ],
        }

    def _median_int(self, values: List[int]) -> int:
        if not values:
            return 0
        values_sorted = sorted(int(v) for v in values)
        n = len(values_sorted)
        mid = n // 2
        if n % 2 == 1:
            return int(values_sorted[mid])
        return int((values_sorted[mid - 1] + values_sorted[mid]) / 2)
