"""Rules tab: edit the organisation rules and save them."""
import os
from collections.abc import Callable
from tkinter import filedialog

import customtkinter
from PIL import Image

from src.config.config_manager import export_config
from src.config.rules import (
    CONDITION_FIELDS,
    DATE_GRANULARITIES,
    MATCH_MODES,
    SORT_MODES,
    SORT_ORDERS,
    TEXT_OPERATORS,
    Condition,
    FormatCategory,
    RulesConfig,
)
from src.gui.widgets import CollapsibleSection

SORT_MODE_LABELS = {"none": "No sorting", "date": "By date", "name": "By name"}
_LABEL_TO_SORT_MODE = {label: mode for mode, label in SORT_MODE_LABELS.items()}
ORDER_LABELS = {"asc": "Ascending", "desc": "Descending"}
_LABEL_TO_ORDER = {label: order for order, label in ORDER_LABELS.items()}
FIELD_LABELS = {"extension": "Extension", "name": "Name", "path": "Path"}
_LABEL_TO_FIELD = {label: key for key, label in FIELD_LABELS.items()}
OP_LABELS = {
    "contains": "contains",
    "starts_with": "starts with",
    "ends_with": "ends with",
    "equals": "equals",
}
_LABEL_TO_OP = {label: key for key, label in OP_LABELS.items()}
MATCH_LABELS = {"all": "All", "any": "Any", "none": "None"}
_LABEL_TO_MATCH = {label: key for key, label in MATCH_LABELS.items()}
_ICON_SIZE = (20, 20)
_ICON_FILETYPES = [("Images", "*.ico *.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")]
_EXT_PLACEHOLDER = "jpg, png, ..."
_TEXT_PLACEHOLDER = "text to match"


def _load_icon(path: str):
    """Return a CTkImage for the image at ``path``, or None if it cannot load."""
    try:
        image = Image.open(path)
    except (OSError, ValueError):
        return None
    return customtkinter.CTkImage(light_image=image, dark_image=image, size=_ICON_SIZE)


class RulesTab(customtkinter.CTkScrollableFrame):
    """Editable view of the organisation rules (the whole tab scrolls)."""

    def __init__(
        self,
        master,
        config: RulesConfig,
        on_save: Callable[[RulesConfig], None],
        on_import: Callable[[str], None] | None = None,
        notify: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_save = on_save
        self._on_import = on_import
        self._notify = notify
        self._category_cards: list[dict] = []

        self.grid_columnconfigure(0, weight=1)

        watch_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        watch_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        watch_frame.grid_columnconfigure(1, weight=1)

        customtkinter.CTkLabel(watch_frame, text="Watched folder:").grid(row=0, column=0, sticky="w")
        self._watch_dir = customtkinter.CTkEntry(
            watch_frame, placeholder_text="select or type a folder path"
        )
        self._watch_dir.insert(0, config.watch.directory)
        self._watch_dir.grid(row=0, column=1, sticky="ew", padx=8, pady=2)
        customtkinter.CTkButton(
            watch_frame, text="Browse…", width=80, command=lambda: self._browse_into(self._watch_dir)
        ).grid(row=0, column=2, pady=2)

        customtkinter.CTkLabel(watch_frame, text="Output folder:").grid(row=1, column=0, sticky="w")
        self._output_dir = customtkinter.CTkEntry(
            watch_frame, placeholder_text="where organised files go"
        )
        self._output_dir.insert(0, config.watch.output)
        self._output_dir.grid(row=1, column=1, sticky="ew", padx=8, pady=2)
        customtkinter.CTkButton(
            watch_frame, text="Browse…", width=80, command=lambda: self._browse_into(self._output_dir)
        ).grid(row=1, column=2, pady=2)

        self._recursive = customtkinter.CTkSwitch(watch_frame, text="Include subfolders")
        self._recursive.grid(row=2, column=0, columnspan=3, sticky="w", pady=(6, 0))
        if config.watch.recursive:
            self._recursive.select()

        section = CollapsibleSection(self, title="Organise files by format", expanded=True)
        section.grid(row=1, column=0, sticky="ew", padx=10, pady=(10, 5))

        customtkinter.CTkLabel(section.body, text="Categories").grid(
            row=0, column=0, sticky="w", pady=(0, 2)
        )
        self._categories_frame = customtkinter.CTkFrame(section.body, fg_color="transparent")
        self._categories_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        self._categories_frame.grid_columnconfigure(0, weight=1)
        for category in config.format_rules.categories:
            self._add_category_card(category)

        self._add_category_btn = customtkinter.CTkButton(
            section.body, text="+ Add category", command=self._add_empty_category
        )
        self._add_category_btn.grid(row=2, column=0, sticky="w", pady=5)

        sort_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        sort_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(10, 5))
        sort_frame.grid_columnconfigure(1, weight=1)

        customtkinter.CTkLabel(sort_frame, text="Sort matched files by:").grid(
            row=0, column=0, sticky="w", pady=4
        )
        self._sort_mode = customtkinter.CTkOptionMenu(
            sort_frame,
            values=[SORT_MODE_LABELS[m] for m in SORT_MODES],
            command=lambda _value: self._sync_sort_state(),
        )
        self._sort_mode.set(SORT_MODE_LABELS.get(config.sort.mode, SORT_MODE_LABELS["none"]))
        self._sort_mode.grid(row=0, column=1, sticky="w", padx=10)

        customtkinter.CTkLabel(sort_frame, text="Order:").grid(row=1, column=0, sticky="w", pady=4)
        self._sort_order = customtkinter.CTkOptionMenu(
            sort_frame, values=[ORDER_LABELS[o] for o in SORT_ORDERS]
        )
        self._sort_order.set(ORDER_LABELS.get(config.sort.order, ORDER_LABELS["asc"]))
        self._sort_order.grid(row=1, column=1, sticky="w", padx=10)

        self._date_label = customtkinter.CTkLabel(sort_frame, text="Date detail:")
        self._date_label.grid(row=2, column=0, sticky="w", pady=4)
        self._date_granularity = customtkinter.CTkOptionMenu(
            sort_frame, values=list(DATE_GRANULARITIES)
        )
        self._date_granularity.set(config.sort.date_granularity)
        self._date_granularity.grid(row=2, column=1, sticky="w", padx=10)

        io_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        io_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(10, 0))
        io_frame.grid_columnconfigure((0, 1), weight=1)
        customtkinter.CTkButton(io_frame, text="Import rules…", command=self._import).grid(
            row=0, column=0, padx=(0, 5), sticky="ew"
        )
        customtkinter.CTkButton(io_frame, text="Export rules…", command=self._export).grid(
            row=0, column=1, padx=(5, 0), sticky="ew"
        )

        save_btn = customtkinter.CTkButton(self, text="Save rules", command=self._save)
        save_btn.grid(row=4, column=0, sticky="ew", padx=10, pady=(8, 10))

        self._sync_sort_state()

    def _add_empty_category(self) -> None:
        self._add_category_card(
            FormatCategory(name="", folder="", conditions=[Condition(field="extension", value="")]),
            expanded=True,
        )

    def _add_category_card(self, category: FormatCategory, expanded: bool = False) -> None:
        row = len(self._category_cards)
        card = customtkinter.CTkFrame(self._categories_frame)
        card.grid(row=row, column=0, sticky="ew", pady=4, padx=2)
        card.grid_columnconfigure(0, weight=1)

        record: dict = {
            "card": card,
            "icon_path": category.icon,
            "icon_image": _load_icon(category.icon) if category.icon else None,
            "condition_rows": [],
        }

        header = customtkinter.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 2))
        header.grid_columnconfigure(2, weight=1)
        record["header"] = header

        toggle = customtkinter.CTkButton(
            header,
            text=self._chevron(expanded),
            width=28,
            fg_color="transparent",
            command=lambda: self._toggle_card(record),
        )
        toggle.grid(row=0, column=0, padx=(0, 2))
        record["toggle_btn"] = toggle

        self._build_icon_button(record)

        folder = customtkinter.CTkEntry(header, placeholder_text="folder name")
        folder.insert(0, category.folder)
        folder.grid(row=0, column=2, sticky="ew", padx=2)
        record["folder"] = folder

        customtkinter.CTkLabel(header, text="Match:").grid(row=0, column=3, padx=(8, 2))
        match_menu = customtkinter.CTkOptionMenu(
            header, width=80, values=[MATCH_LABELS[m] for m in MATCH_MODES]
        )
        match_menu.set(MATCH_LABELS.get(category.match, MATCH_LABELS["any"]))
        match_menu.grid(row=0, column=4, padx=2)
        record["match_menu"] = match_menu

        remove = customtkinter.CTkButton(
            header, text="✕", width=28, command=lambda: self._remove_card(record)
        )
        remove.grid(row=0, column=5, padx=(6, 0))
        record["remove"] = remove

        conditions_frame = customtkinter.CTkFrame(card, fg_color="transparent")
        conditions_frame.grid(row=1, column=0, sticky="ew", padx=6, pady=(10, 4))
        conditions_frame.grid_columnconfigure(0, weight=1)
        record["conditions_frame"] = conditions_frame
        for condition in category.conditions:
            self._add_condition_row(record, condition)

        add_cond = customtkinter.CTkButton(
            card, text="+ Add condition", height=24, command=lambda: self._add_condition(record)
        )
        add_cond.grid(row=2, column=0, sticky="w", padx=6, pady=(0, 6))
        record["add_cond_btn"] = add_cond

        record["expanded"] = expanded
        if not expanded:
            conditions_frame.grid_remove()
            add_cond.grid_remove()

        self._category_cards.append(record)

    def _remove_card(self, record: dict) -> None:
        record["card"].destroy()
        self._category_cards.remove(record)

    @staticmethod
    def _chevron(expanded: bool) -> str:
        return "▾" if expanded else "▸"

    def _toggle_card(self, record: dict) -> None:
        """Show or hide a category's conditions."""
        record["expanded"] = not record["expanded"]
        if record["expanded"]:
            record["conditions_frame"].grid()
            record["add_cond_btn"].grid()
        else:
            record["conditions_frame"].grid_remove()
            record["add_cond_btn"].grid_remove()
        record["toggle_btn"].configure(text=self._chevron(record["expanded"]))

    def _build_icon_button(self, record: dict) -> None:
        """(Re)create the card's icon button (rebuilt, not configured: CTk 5.2.2 image bug)."""
        existing = record.get("icon_btn")
        if existing is not None:
            existing.destroy()
        image = record["icon_image"]
        parent = record["header"]
        if image is not None:
            button = customtkinter.CTkButton(
                parent, text="", image=image, width=36, command=lambda: self._pick_icon(record)
            )
        else:
            button = customtkinter.CTkButton(
                parent, text="📁", width=36, command=lambda: self._pick_icon(record)
            )
        button.grid(row=0, column=1, padx=(0, 6))
        record["icon_btn"] = button

    def _apply_icon(self, record: dict, path: str) -> None:
        """Load the icon at ``path`` and rebuild the card's button to show it."""
        image = _load_icon(path)
        if image is None:
            return
        record["icon_path"] = path
        record["icon_image"] = image  # keep a reference so Tk does not drop it
        self._build_icon_button(record)

    def _pick_icon(self, record: dict) -> None:
        path = filedialog.askopenfilename(title="Choose a folder icon", filetypes=_ICON_FILETYPES)
        if path:
            self._apply_icon(record, path)

    def _browse_into(self, entry: customtkinter.CTkEntry) -> None:
        current = entry.get().strip()
        initial = current if os.path.isdir(current) else os.getcwd()
        path = filedialog.askdirectory(title="Choose a folder", initialdir=initial)
        if path:
            entry.delete(0, "end")
            entry.insert(0, path)

    def _add_condition(self, card_record: dict) -> None:
        self._add_condition_row(card_record, Condition(field="extension", value=""))

    def _add_condition_row(self, card_record: dict, condition: Condition) -> None:
        parent = card_record["conditions_frame"]
        row = len(card_record["condition_rows"])
        frame = customtkinter.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", pady=4)
        frame.grid_columnconfigure(2, weight=1)

        cr: dict = {"frame": frame}

        field_menu = customtkinter.CTkOptionMenu(
            frame,
            width=100,
            values=[FIELD_LABELS[f] for f in CONDITION_FIELDS],
            command=lambda _value: self._sync_condition_operator(cr),
        )
        field_menu.set(FIELD_LABELS.get(condition.field, FIELD_LABELS["extension"]))
        field_menu.grid(row=0, column=0, padx=(0, 4))
        cr["field_menu"] = field_menu

        op_menu = customtkinter.CTkOptionMenu(
            frame, width=100, values=[OP_LABELS[o] for o in TEXT_OPERATORS]
        )
        op_menu.set(OP_LABELS.get(condition.operator, OP_LABELS["contains"]))
        op_menu.grid(row=0, column=1, padx=4)
        cr["op_menu"] = op_menu

        value = customtkinter.CTkEntry(frame, placeholder_text=_EXT_PLACEHOLDER)
        value.insert(0, condition.value)
        value.grid(row=0, column=2, sticky="ew", padx=4)
        cr["value"] = value

        remove = customtkinter.CTkButton(
            frame, text="✕", width=28, command=lambda: self._remove_condition_row(card_record, cr)
        )
        remove.grid(row=0, column=3, padx=(4, 0))
        cr["remove"] = remove

        card_record["condition_rows"].append(cr)
        self._sync_condition_operator(cr)

    def _remove_condition_row(self, card_record: dict, cr: dict) -> None:
        cr["frame"].destroy()
        card_record["condition_rows"].remove(cr)

    def _sync_condition_operator(self, cr: dict) -> None:
        """The operator menu applies only to name/path; extension uses a list."""
        is_text = _LABEL_TO_FIELD.get(cr["field_menu"].get(), "extension") in ("name", "path")
        cr["op_menu"].configure(state="normal" if is_text else "disabled")
        cr["value"].configure(placeholder_text=_TEXT_PLACEHOLDER if is_text else _EXT_PLACEHOLDER)

    def _sync_sort_state(self) -> None:
        """Enable order for any active sort; show date detail only for date sort."""
        mode = _LABEL_TO_SORT_MODE.get(self._sort_mode.get(), "none")
        self._sort_order.configure(state="normal" if mode != "none" else "disabled")
        if mode == "date":
            self._date_label.grid()
            self._date_granularity.grid()
        else:
            self._date_label.grid_remove()
            self._date_granularity.grid_remove()

    def _collect(self) -> RulesConfig:
        config = RulesConfig()
        for card in self._category_cards:
            folder = card["folder"].get().strip()
            conditions = []
            for cr in card["condition_rows"]:
                value = cr["value"].get().strip()
                if not value:
                    continue
                conditions.append(
                    Condition(
                        field=_LABEL_TO_FIELD.get(cr["field_menu"].get(), "extension"),
                        operator=_LABEL_TO_OP.get(cr["op_menu"].get(), "contains"),
                        value=value,
                    )
                )
            if not folder and not conditions:
                continue
            config.format_rules.categories.append(
                FormatCategory(
                    name=folder,
                    folder=folder,
                    match=_LABEL_TO_MATCH.get(card["match_menu"].get(), "any"),
                    conditions=conditions,
                    icon=card["icon_path"],
                )
            )
        config.sort.mode = _LABEL_TO_SORT_MODE.get(self._sort_mode.get(), "none")
        config.sort.order = _LABEL_TO_ORDER.get(self._sort_order.get(), "asc")
        config.sort.date_granularity = self._date_granularity.get()
        config.watch.directory = self._watch_dir.get().strip()
        config.watch.output = self._output_dir.get().strip()
        config.watch.recursive = bool(self._recursive.get())
        return config

    def _export(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export rules",
            defaultextension=".yaml",
            initialfile="organiser_rules.yaml",
            initialdir=os.getcwd(),
            filetypes=[("YAML", "*.yaml *.yml"), ("All files", "*.*")],
        )
        if not path:
            return
        export_config(self._collect(), path)
        if self._notify:
            self._notify("Rules exported")

    def _import(self) -> None:
        path = filedialog.askopenfilename(
            title="Import rules",
            initialdir=os.getcwd(),
            filetypes=[("YAML", "*.yaml *.yml"), ("All files", "*.*")],
        )
        if path and self._on_import:
            self._on_import(path)

    def _save(self) -> None:
        self._on_save(self._collect())
