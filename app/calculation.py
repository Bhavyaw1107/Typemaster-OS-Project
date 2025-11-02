from typing import List

def compute_wpm_series(correct_flags: List[bool], timestamps: List[float]) -> List[float]:
    if not correct_flags or not timestamps:
        return []
    t0 = timestamps[0]
    wpm_series, correct = [], 0
    for i, ok in enumerate(correct_flags):
        if ok:
            correct += 1
        seconds = max(0.001, timestamps[i] - t0)
        wpm = (correct / 5.0) / (seconds / 60.0)
        wpm_series.append(wpm)
    return wpm_series

def smooth(values: List[float], factor: float = 0.25) -> List[float]:
    out, last = [], None
    for v in values:
        last = v if last is None else last + factor * (v - last)
        out.append(last)
    return out
