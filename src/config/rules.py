"""Typed (dataclass) representation of the organisation rules; list order = priority."""
from dataclasses import dataclass, field

SORT_MODES = ("none", "date", "name")
SORT_ORDERS = ("asc", "desc")
DATE_GRANULARITIES = ("year", "month", "day")
CONDITION_FIELDS = ("extension", "name", "path")
TEXT_OPERATORS = ("contains", "starts_with", "ends_with", "equals")
MATCH_MODES = ("all", "any", "none")


def _normalise_extensions(values: list) -> list[str]:
    """Lower-case extensions and strip any leading dots, dropping blanks."""
    return [str(v).strip().lower().lstrip(".") for v in values if str(v).strip()]


@dataclass
class Condition:
    """A single test against a file: an extension list, or a name/path match.

    ``operator`` applies to the ``name``/``path`` fields; for ``extension`` the
    value is a comma-separated list and the operator is ignored.
    """

    field: str = "extension"
    operator: str = "contains"
    value: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Condition":
        field_ = data.get("field", "extension")
        operator = data.get("operator", "contains")
        return cls(
            field=field_ if field_ in CONDITION_FIELDS else "extension",
            operator=operator if operator in TEXT_OPERATORS else "contains",
            value=str(data.get("value", "")),
        )

    def to_dict(self) -> dict:
        return {"field": self.field, "operator": self.operator, "value": self.value}


@dataclass
class FormatCategory:
    """A destination folder plus the conditions a file must meet to go there.

    ``match`` controls how the conditions combine: all | any | none. ``icon``
    is an optional image used as the folder's icon (in the app, and on the
    Windows folder once the organizer runs).
    """

    name: str
    folder: str
    match: str = "any"
    conditions: list[Condition] = field(default_factory=list)
    icon: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "FormatCategory":
        name = data.get("name", "")
        raw_conditions = data.get("conditions")
        if raw_conditions:
            conditions = [Condition.from_dict(c) for c in raw_conditions]
        else:
            # legacy form: an "extensions" list becomes one extension condition
            extensions = _normalise_extensions(data.get("extensions") or [])
            conditions = (
                [Condition(field="extension", value=", ".join(extensions))] if extensions else []
            )
        match = data.get("match", "any")
        return cls(
            name=name,
            folder=data.get("folder") or name,
            match=match if match in MATCH_MODES else "any",
            conditions=conditions,
            icon=data.get("icon", "") or "",
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "folder": self.folder,
            "match": self.match,
            "conditions": [c.to_dict() for c in self.conditions],
            "icon": self.icon,
        }


@dataclass
class FormatRules:
    """The ordered list of category rules (priority = list order)."""

    categories: list[FormatCategory] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "FormatRules":
        return cls(categories=[FormatCategory.from_dict(c) for c in data.get("categories") or []])

    def to_dict(self) -> dict:
        return {"categories": [c.to_dict() for c in self.categories]}


@dataclass
class SortSettings:
    """Optional ordering of matched files by date or name, ascending/descending."""

    mode: str = "none"
    order: str = "asc"
    date_granularity: str = "month"

    @classmethod
    def from_dict(cls, data: dict) -> "SortSettings":
        mode = data.get("mode", "none")
        order = data.get("order", "asc")
        granularity = data.get("date_granularity", "month")
        return cls(
            mode=mode if mode in SORT_MODES else "none",
            order=order if order in SORT_ORDERS else "asc",
            date_granularity=granularity if granularity in DATE_GRANULARITIES else "month",
        )

    def to_dict(self) -> dict:
        return {"mode": self.mode, "order": self.order, "date_granularity": self.date_granularity}


@dataclass
class WatchSettings:
    """Which folder to watch, where to move matched files, and recursion."""

    directory: str = ""
    output: str = ""
    recursive: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "WatchSettings":
        return cls(
            directory=str(data.get("directory", "")),
            output=str(data.get("output", "")),
            recursive=bool(data.get("recursive", True)),
        )

    def to_dict(self) -> dict:
        return {
            "directory": self.directory,
            "output": self.output,
            "recursive": self.recursive,
        }


@dataclass
class RulesConfig:
    """The full organisation configuration."""

    watch: WatchSettings = field(default_factory=WatchSettings)
    format_rules: FormatRules = field(default_factory=FormatRules)
    sort: SortSettings = field(default_factory=SortSettings)

    @classmethod
    def from_dict(cls, data: dict) -> "RulesConfig":
        data = data or {}
        return cls(
            watch=WatchSettings.from_dict(data.get("watch") or {}),
            format_rules=FormatRules.from_dict(data.get("format_rules") or {}),
            sort=SortSettings.from_dict(data.get("sort") or {}),
        )

    def to_dict(self) -> dict:
        return {
            "watch": self.watch.to_dict(),
            "format_rules": self.format_rules.to_dict(),
            "sort": self.sort.to_dict(),
        }
