"""Sandwich-attack detector per PRD §6.1."""

from __future__ import annotations

from collections import defaultdict

from .types import DetectSwap, SandwichCandidate

# Safety: if extractor somehow "doubles" their input, it's almost certainly
# not a sandwich — likely multi-hop or data-quality artefact.
MAX_PROFIT_RATIO = 2


def same_actor(a: DetectSwap, b: DetectSwap) -> bool:
    """One actor if same signer OR same contract called (both non-null)."""
    if a.sender == b.sender:
        return True
    if a.tx_to is not None and b.tx_to is not None and a.tx_to == b.tx_to:
        return True
    return False


def detect_sandwiches(swaps: list[DetectSwap]) -> list[SandwichCandidate]:
    by_pool: dict[bytes, list[DetectSwap]] = defaultdict(list)
    for s in swaps:
        by_pool[s.pool].append(s)

    results: list[SandwichCandidate] = []
    for pool, pool_swaps in by_pool.items():
        if len(pool_swaps) < 3:
            continue
        pool_swaps.sort(key=lambda s: (s.tx_index, s.log_index))

        consumed: set[int] = set()   # indices already used as front or back

        for i in range(len(pool_swaps) - 2):
            if i in consumed:
                continue
            front = pool_swaps[i]
            for k in range(i + 2, len(pool_swaps)):
                if k in consumed:
                    continue
                back = pool_swaps[k]
                if front.tx_hash == back.tx_hash:
                    continue              # same tx can't sandwich itself
                if not same_actor(front, back):
                    continue
                # Back must reverse the front's swap direction.
                if front.token_in != back.token_out or front.token_out != back.token_in:
                    continue
                # At least one victim between: same direction as front, different actor.
                victim: DetectSwap | None = None
                for j in range(i + 1, k):
                    v = pool_swaps[j]
                    if (v.token_in == front.token_in
                            and v.token_out == front.token_out
                            and not same_actor(v, front)):
                        victim = v
                        break
                if victim is None:
                    continue
                # Economic check: back returned more than front sent in.
                if back.amount_out <= front.amount_in:
                    continue
                if back.amount_out > front.amount_in * MAX_PROFIT_RATIO:
                    continue

                results.append(SandwichCandidate(pool=pool, front=front, victim=victim, back=back))
                consumed.add(i)
                consumed.add(k)
                break   # one back per front
    return results
