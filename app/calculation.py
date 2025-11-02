from typing import List, Tuple
import bisect

def compute_wpm_series(correct_flags: List[bool], timestamps: List[float]) -> List[float]:
    """
    Legacy cumulative WPM (kept for compatibility). Left here in case you want it.
    """
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

def rolling_wpm(correct_flags: List[bool], timestamps: List[float], window_sec: float = 10.0) -> List[float]:
    """
    Monkeytype-like: WPM computed over a sliding window (default 10s).
    WPM = (correct chars in window / 5) / (window / 60)
    Returns a value per keystroke timestamp.
    """
    n = len(timestamps)
    if n == 0:
        return []
    out: List[float] = []
    start_idx = 0
    for i in range(n):
        t_now = timestamps[i]
        # move start index to keep window within [t_now - window_sec, t_now]
        while start_idx < i and timestamps[start_idx] < t_now - window_sec:
            start_idx += 1
        # count correct chars within window
        correct = 0
        for j in range(start_idx, i + 1):
            if correct_flags[j]:
                correct += 1
        dur = max(0.5, timestamps[i] - max(timestamps[start_idx], t_now - window_sec))  # avoid spikes
        out.append((correct / 5.0) / (dur / 60.0))
    return out
