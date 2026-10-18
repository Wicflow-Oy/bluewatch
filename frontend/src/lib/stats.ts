// Small-sample statistics for the Precision screen. The report's notes carry the same intervals, but
// as translated prose rounded to three decimals; computing them here keeps every language identical
// and lets the screen floor the exact bounds instead of a rounded figure.

/** Wilson score interval for k successes out of n, the same formula as bluewatch/evals/stats.py. */
export function wilson(k: number, n: number, z = 1.96): [number, number] {
  if (n <= 0 || k < 0 || k > n)
    throw new RangeError(`wilson(${k}, ${n}): needs 0 <= k <= n and n > 0`);
  const p = k / n;
  const d = 1 + (z * z) / n;
  const centre = (p + (z * z) / (2 * n)) / d;
  const half = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / d;
  return [Math.max(0, centre - half), Math.min(1, centre + half)];
}
