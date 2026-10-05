import re
from workflow.environment import max_gap

def select(hyps, max_k=10):
    
    best, kept, seen = hyps[0].score, [], set()
    for h in hyps:
        if len(kept) >= max_k:
            break
        if kept and best - h.score > max_gap():
            break  # sorted best-first, so everything after is worse
        key = re.sub(r"[\W_]+", " ", h.text.casefold()).strip()
        if key not in seen:  # drop case/punctuation-only duplicates
            seen.add(key); kept.append(h)
    return kept