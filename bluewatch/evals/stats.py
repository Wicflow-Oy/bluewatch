"""Agreement statistics: Wilson intervals for proportions, quadratic weighted kappa on ordinal bands, and a
seeded bootstrap interval for kappa."""

from __future__ import annotations

import math
import random


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(centre - half, 3), round(centre + half, 3)


def qwk(truth: list[int], pred: list[int], k: int = 3) -> float | None:
    """Quadratic weighted kappa on labels 0..k-1; None when it is undefined (e.g. one class only)."""
    n = len(truth)
    if n == 0:
        return None
    observed = [[0] * k for _ in range(k)]
    for t, p in zip(truth, pred, strict=True):
        observed[t][p] += 1
    rows = [sum(observed[i]) for i in range(k)]
    cols = [sum(observed[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = (i - j) ** 2 / (k - 1) ** 2
            num += w * observed[i][j]
            den += w * rows[i] * cols[j] / n
    return None if den == 0 else round(1 - num / den, 3)


def kappa_interval(truth: list[int], pred: list[int], iters: int = 1000, seed: int = 7) -> tuple[float, float] | None:
    rnd = random.Random(seed)
    idx = range(len(truth))
    values = []
    for _ in range(iters):
        sample = [rnd.choice(idx) for _ in idx]
        value = qwk([truth[i] for i in sample], [pred[i] for i in sample])
        if value is not None:
            values.append(value)
    if len(values) < 50:
        return None
    values.sort()
    return values[int(0.025 * len(values))], values[int(0.975 * len(values)) - 1]
