"""Anonymization, ranking parsing, and aggregate scoring for Stage 2."""

import re
from collections import defaultdict
from typing import Any

LABEL_PATTERN = re.compile(r"Response [A-Z]")
NUMBERED_LABEL_PATTERN = re.compile(r"\d+\.\s*(Response [A-Z])")


def build_label_to_model(stage1: list[dict[str, Any]]) -> dict[str, str]:
    """Assign anonymous labels ("Response A", "Response B", ...) in Stage 1 order."""
    return {f"Response {chr(65 + i)}": r["model"] for i, r in enumerate(stage1)}


def parse_ranking(ranking_text: str) -> list[str]:
    """
    Extract the ranked labels from a model's evaluation.

    Prefers the numbered list after "FINAL RANKING:"; falls back to any
    "Response X" mentions in order if the model didn't follow the format.
    """
    if "FINAL RANKING:" in ranking_text:
        section = ranking_text.split("FINAL RANKING:", 1)[1]
        numbered = NUMBERED_LABEL_PATTERN.findall(section)
        return numbered or LABEL_PATTERN.findall(section)

    return LABEL_PATTERN.findall(ranking_text)


def aggregate_rankings(
    stage2: list[dict[str, Any]],
    label_to_model: dict[str, str],
) -> list[dict[str, Any]]:
    """
    Average each model's position across all peer evaluations.

    Returns:
        [{"model", "average_rank", "rankings_count"}, ...] sorted best (lowest) first
    """
    positions: dict[str, list[int]] = defaultdict(list)

    for evaluation in stage2:
        for position, label in enumerate(parse_ranking(evaluation["ranking"]), start=1):
            if label in label_to_model:
                positions[label_to_model[label]].append(position)

    aggregate = [
        {
            "model": model,
            "average_rank": round(sum(ranks) / len(ranks), 2),
            "rankings_count": len(ranks),
        }
        for model, ranks in positions.items()
    ]
    return sorted(aggregate, key=lambda x: x["average_rank"])
