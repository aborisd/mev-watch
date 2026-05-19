"""JIT-liquidity detector per PRD §6.2."""

from __future__ import annotations

from collections import defaultdict
from typing import Literal

from .types import DetectLiq, DetectSwap, JITCandidate

_EventTag = Literal["swap", "mint", "burn"]


def detect_jits(swaps: list[DetectSwap], liqs: list[DetectLiq]) -> list[JITCandidate]:
    # Only V3 swaps matter for JIT (V3 liquidity events come from V3 pools).
    by_pool_events: dict[bytes, list[tuple[_EventTag, object]]] = defaultdict(list)
    for s in swaps:
        if s.protocol == "uni_v3":
            by_pool_events[s.pool].append(("swap", s))
    for l in liqs:
        by_pool_events[l.pool].append((l.event_type, l))    # type: ignore[arg-type]

    results: list[JITCandidate] = []
    for pool, events in by_pool_events.items():
        events.sort(key=lambda e: (e[1].tx_index, e[1].log_index))  # type: ignore[attr-defined]

        consumed_burns: set[int] = set()
        for mi, (tag, m) in enumerate(events):
            if tag != "mint":
                continue
            mint: DetectLiq = m  # type: ignore[assignment]
            # Find matching burn (same owner, ticks, liquidity) strictly after.
            for bi in range(mi + 1, len(events)):
                if bi in consumed_burns:
                    continue
                btag, b = events[bi]
                if btag != "burn":
                    continue
                burn: DetectLiq = b  # type: ignore[assignment]
                if (burn.owner != mint.owner
                        or burn.tick_lower != mint.tick_lower
                        or burn.tick_upper != mint.tick_upper
                        or burn.liquidity != mint.liquidity):
                    continue
                # Victim check: at least one swap between mint and burn that is
                # NOT in the same tx as the mint/burn (otherwise it's a self-swap,
                # not a 3rd-party victim — common pattern for flash-loan callbacks).
                victim: DetectSwap | None = None
                for ki in range(mi + 1, bi):
                    tag2, e = events[ki]
                    if tag2 != "swap":
                        continue
                    cand: DetectSwap = e  # type: ignore[assignment]
                    if cand.tx_hash == mint.tx_hash or cand.tx_hash == burn.tx_hash:
                        continue
                    if cand.sender == mint.sender:
                        continue
                    victim = cand
                    break
                if victim is None:
                    break   # no victim between this mint & burn — stop
                results.append(JITCandidate(pool=pool, mint=mint, burn=burn, victim=victim))
                consumed_burns.add(bi)
                break
    return results
