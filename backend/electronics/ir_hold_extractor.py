from typing import List, Optional, Tuple

from .ir_signal_aggregator import IrSignalAggregator


class IrHoldExtractor:
    def __init__(self, aggregator: IrSignalAggregator) -> None:
        self._aggregator = aggregator

    def extract(
        self,
        frames: List[List[int]],
        round_to_us: int,
        min_match_ratio: float,
    ) -> Tuple[List[int], Optional[List[int]], int, Optional[float]]:
        if not frames:
            raise ValueError("frames must not be empty")

        hold_initial = frames[0]
        repeats = frames[1:]
        if not repeats:
            return hold_initial, None, 0, None

        repeat_frame, repeat_indices, score = self._aggregator.aggregate(
            repeats,
            round_to_us=round_to_us,
            min_match_ratio=min_match_ratio,
        )
        return hold_initial, repeat_frame, len(repeat_indices), score
