"""Pure classification: match a file to its destination category."""
from pathlib import Path

from src.config.rules import Condition, FormatCategory, RulesConfig


def _condition_matches(condition: Condition, path: Path) -> bool:
    if condition.field == "extension":
        wanted = {e.strip().lower().lstrip(".") for e in condition.value.split(",") if e.strip()}
        return path.suffix.lower().lstrip(".") in wanted

    value = condition.value.strip().lower()
    if not value:
        return False
    target = path.stem.lower() if condition.field == "name" else str(path).lower()
    if condition.operator == "starts_with":
        return target.startswith(value)
    if condition.operator == "ends_with":
        return target.endswith(value)
    if condition.operator == "equals":
        return target == value
    return value in target


def _category_matches(category: FormatCategory, path: Path) -> bool:
    if not category.conditions:
        return False
    results = [_condition_matches(c, path) for c in category.conditions]
    if category.match == "all":
        return all(results)
    if category.match == "none":
        return not any(results)
    return any(results)


def classify(path: Path, rules: RulesConfig) -> FormatCategory | None:
    """Return the first category (by priority order) whose conditions match, else None."""
    for category in rules.format_rules.categories:
        if category.folder and _category_matches(category, path):
            return category
    return None
