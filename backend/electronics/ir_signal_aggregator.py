import math
from typing import Dict, List, Tuple


class IrSignalAggregator:
    def aggregate(
        self,
        frames: List[List[int]],
        round_to_us: int,
        min_match_ratio: float,
    ) -> Tuple[List[int], List[int], float]:
        if not frames:
            raise ValueError("frames must not be empty")
        if round_to_us <= 0:
            raise ValueError("round_to_us must be > 0")
        if min_match_ratio <= 0 or min_match_ratio > 1:
            raise ValueError("min_match_ratio must be in (0, 1]")

        clusters: Dict[Tuple[int, Tuple[int, ...]], List[int]] = {}
        for idx, frame in enumerate(frames):
            if not frame:
                continue
            key = (len(frame), tuple(1 if v > 0 else -1 for v in frame))
            clusters.setdefault(key, []).append(idx)

        if not clusters:
            raise ValueError("No valid frames to aggregate")

        # Pick the dominant cluster (same length and sign pattern).
        best_key, best_indices = max(clusters.items(), key=lambda kv: len(kv[1]))
        required = max(1, int(math.ceil(len(frames) * min_match_ratio)))
        if len(best_indices) < required:
            raise ValueError(
                f"Not enough matching takes (need {required}, got {len(best_indices)}). "
                "Increase takes or improve capture conditions."
            )

        length = best_key[0]
        pattern = best_key[1]

        # Median aggregation by position.
        aggregated: List[int] = []
        for i in range(length):
            values = sorted(abs(frames[idx][i]) for idx in best_indices)
            m = self._median_int(values)
            rounded = int(round(m / round_to_us) * round_to_us)
            sign = 1 if pattern[i] > 0 else -1
            aggregated.append(sign * max(1, rounded))

        score = self._quality_score(frames, best_indices, aggregated)
        return aggregated, best_indices, score

    def _median_int(self, values: List[int]) -> int:
        if not values:
            return 0
        n = len(values)
        mid = n // 2
        if n % 2 == 1:
            return int(values[mid])
        return int((values[mid - 1] + values[mid]) / 2)

    def _quality_score(self, frames: List[List[int]], indices: List[int], aggregated: List[int]) -> float:
        if not indices:
            return 0.0

        length = len(aggregated)
        if length == 0:
            return 0.0

        errors: List[float] = []
        for idx in indices:
            frame = frames[idx]
            if len(frame) != length:
                continue
            diffs = [abs(abs(frame[i]) - abs(aggregated[i])) for i in range(length)]
            errors.append(sum(diffs) / float(length))

        if not errors:
            return 0.0

        mean_error_us = sum(errors) / float(len(errors))

        # Score in [0, 1]. 0.0 means very inconsistent.
        # 500us is an arbitrary cutoff where we consider the signal too noisy.
        return max(0.0, 1.0 - min(1.0, mean_error_us / 500.0))
