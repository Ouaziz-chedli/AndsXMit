"""
Scoring Module - Calculate raw diagnosis scores from similarity scores.

Score calculation: avg(positive_similarities) - avg(negative_similarities)

This provides a baseline score before applying trimester weights and patient priors.
"""

from statistics import mean
from typing import List


def calculate_raw_score(
    positive_sims: List[float],
    negative_sims: List[float],
) -> float:
    """
    Calculate raw diagnosis score from similarity scores.

    Args:
        positive_sims: List of similarity scores from positive (diseased) cases
        negative_sims: List of similarity scores from negative (healthy) cases

    Returns:
        Raw score between -1.0 and 1.0
        - Positive score: More similar to diseased cases
        - Negative score: More similar to healthy cases

    Examples:
        >>> calculate_raw_score([0.85, 0.78, 0.82], [0.30, 0.25, 0.35])
        0.52

        >>> calculate_raw_score([0.30, 0.25], [0.85, 0.78])
        -0.52
    """
    if not positive_sims and not negative_sims:
        return 0.0

    pos_mean = mean(positive_sims) if positive_sims else 0.0
    neg_mean = mean(negative_sims) if negative_sims else 0.0

    return pos_mean - neg_mean


def calculate_confidence_interval(
    positive_sims: List[float],
    negative_sims: List[float],
    confidence: float = 0.95,
) -> tuple[float, float]:
    """
    Calculate confidence interval for the raw score.

    Args:
        positive_sims: List of similarity scores from positive cases
        negative_sims: List of similarity scores from negative cases
        confidence: Confidence level (default 0.95)

    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    if len(positive_sims) < 2 and len(negative_sims) < 2:
        # Not enough data for confidence interval
        raw_score = calculate_raw_score(positive_sims, negative_sims)
        return (raw_score - 0.1, raw_score + 0.1)

    # Simple standard deviation based interval
    import math

    all_sims = positive_sims + negative_sims
    if len(all_sims) < 2:
        raw_score = calculate_raw_score(positive_sims, negative_sims)
        return (raw_score - 0.1, raw_score + 0.1)

    std_dev = math.sqrt(sum((x - mean(all_sims)) ** 2 for x in all_sims) / (len(all_sims) - 1))
    raw_score = calculate_raw_score(positive_sims, negative_sims)

    # 95% confidence: ~2 standard deviations
    margin = 2.0 * std_dev / math.sqrt(len(all_sims))

    return (raw_score - margin, raw_score + margin)
