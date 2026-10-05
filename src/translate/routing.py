from collections import deque
from typing import Iterable

from .types import Language, Pair


def shortest_path(pairs: Iterable[Pair], src: Language, dst: Language,
                  max_hops: int | None = None) -> list[Pair] | None:
    """Fewest-hop chain of pairs from src to dst. [] if src == dst, None if unreachable."""
    if src == dst:
        return []
    edges: dict[Language, list[Pair]] = {}
    for p in pairs:
        edges.setdefault(p.src, []).append(p)
    prev: dict[Language, Pair] = {}
    seen, queue = {src}, deque([src])
    while queue:
        cur = queue.popleft()
        for p in edges.get(cur, []):
            if p.dst in seen:
                continue
            seen.add(p.dst)
            prev[p.dst] = p
            if p.dst == dst:
                chain, node = [], dst
                while node != src:
                    chain.append(prev[node])
                    node = prev[node].src
                chain.reverse()
                return chain if max_hops is None or len(chain) <= max_hops else None
            queue.append(p.dst)
    return None