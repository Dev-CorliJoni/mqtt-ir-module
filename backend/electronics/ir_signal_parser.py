from typing import List, Optional, Tuple


class IrSignalParser:
    def parse_and_normalize(self, raw: str) -> Tuple[List[int], Optional[int]]:
        tokens = self._parse_tokens(raw)
        if not tokens:
            raise ValueError("No tokens parsed from raw capture")

        tail_gap_us: Optional[int] = None
        if tokens and tokens[-1] < 0:
            tail_gap_us = abs(int(tokens[-1]))

        pulses = self._normalize(tokens)
        if not pulses:
            raise ValueError("Normalized signal is empty")
        return pulses, tail_gap_us

    def encode_pulses(self, pulses: List[int]) -> str:
        return " ".join(str(int(v)) for v in pulses)

    def decode_pulses(self, text: str) -> List[int]:
        out: List[int] = []
        for part in (text or "").strip().split():
            out.append(int(part))
        return out

    def to_pulse_space_text(self, pulses: List[int]) -> str:
        # ir-ctl expects alternating lines of "pulse" and "space" durations.
        # The sequence should start and end with a pulse (positive).
        lines: List[str] = []
        for v in pulses:
            if v > 0:
                lines.append(f"pulse {int(v)}")
            else:
                lines.append(f"space {abs(int(v))}")
        return "\n".join(lines) + "\n"

    def _parse_tokens(self, raw: str) -> List[int]:
        raw = (raw or "").strip()
        if not raw:
            return []

        parts = raw.replace("\t", " ").split()
        out: List[int] = []

        i = 0
        while i < len(parts):
            p = parts[i].strip()
            low = p.lower()

            if p.startswith("+") or p.startswith("-"):
                try:
                    out.append(int(p))
                except Exception:
                    pass
                i += 1
                continue

            if low in ("pulse", "space") and i + 1 < len(parts):
                try:
                    value = int(parts[i + 1])
                except Exception:
                    i += 2
                    continue
                out.append(value if low == "pulse" else -value)
                i += 2
                continue

            # Ignore metadata like "carrier 38000"
            if low in ("carrier", "frequency") and i + 1 < len(parts):
                i += 2
                continue

            i += 1

        return out

    def _normalize(self, pulses: List[int]) -> List[int]:
        # Merge consecutive pulses/spaces if the tool ever produces duplicates.
        merged: List[int] = []
        for v in pulses:
            if v == 0:
                continue
            if not merged:
                merged.append(int(v))
                continue

            if (merged[-1] > 0 and v > 0) or (merged[-1] < 0 and v < 0):
                merged[-1] = int(merged[-1]) + int(v)
            else:
                merged.append(int(v))

        # Ensure the sequence starts with a pulse.
        if merged and merged[0] < 0:
            raise ValueError("Signal starts with a space; cannot normalize")

        # Remove trailing spaces (gaps). For sending we want to end on a pulse.
        while merged and merged[-1] < 0:
            merged.pop()

        if not merged:
            return []

        # Ensure alternating sign pattern.
        normalized: List[int] = [merged[0]]
        for v in merged[1:]:
            if (normalized[-1] > 0 and v > 0) or (normalized[-1] < 0 and v < 0):
                normalized[-1] = int(normalized[-1]) + int(v)
            else:
                normalized.append(int(v))

        # Final safety: start/end with pulse.
        if normalized[0] < 0:
            raise ValueError("Normalized signal does not start with a pulse")
        if normalized[-1] < 0:
            raise ValueError("Normalized signal does not end with a pulse")

        return normalized
