import re
import os

def select(hyps, max_k=10):
    max_gap = os.environ.get("ww_max_gap")
    assert max_gap is not None
    best, kept, seen = hyps[0].score, [], set()
    for h in hyps:
        if len(kept) >= max_k:
            break
        if kept and best - h.score > float(max_gap):
            break  # sorted best-first, so everything after is worse
        key = re.sub(r"[\W_]+", " ", h.text.casefold()).strip()
        if key not in seen:  # drop case/punctuation-only duplicates
            seen.add(key); kept.append(h)
    return kept