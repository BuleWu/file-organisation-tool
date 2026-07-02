"""Reusable customtkinter widgets."""
import webbrowser
from tkinter import TclError

import customtkinter
from PIL import Image, ImageDraw

from src.utils.paths import WINDOW_ICON

ICON_PATH = str(WINDOW_ICON)
_COLLAPSED = "▸"
_EXPANDED = "▾"


class CollapsibleSection(customtkinter.CTkFrame):
    """A titled section whose body can be expanded or collapsed via its header.

    Callers add their controls to :attr:`body`; extra header widgets (e.g. an
    enable switch) go into :attr:`header` at column 1 or beyond.
    """

    def __init__(self, master, title: str, expanded: bool = False) -> None:
        super().__init__(master, fg_color="transparent")
        self._title = title
        self._expanded = expanded
        self.grid_columnconfigure(0, weight=1)

        self.header = customtkinter.CTkFrame(self, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_columnconfigure(0, weight=1)

        self._toggle = customtkinter.CTkButton(
            self.header,
            text=self._label(),
            anchor="w",
            fg_color="transparent",
            command=self.toggle,
        )
        self._toggle.grid(row=0, column=0, sticky="ew")

        self.body = customtkinter.CTkFrame(self, fg_color="transparent")
        self.body.grid_columnconfigure(0, weight=1)
        if self._expanded:
            self.body.grid(row=1, column=0, sticky="nsew", padx=(15, 0))

    def _label(self) -> str:
        return f"{_EXPANDED if self._expanded else _COLLAPSED}  {self._title}"

    def toggle(self) -> None:
        """Show or hide the body and update the header indicator."""
        self._expanded = not self._expanded
        if self._expanded:
            self.body.grid(row=1, column=0, sticky="nsew", padx=(15, 0))
        else:
            self.body.grid_remove()
        self._toggle.configure(text=self._label())


def _success_icon() -> Image.Image:
    """A green filled circle with a white check mark, drawn at high res."""
    scale = 4
    size = 18 * scale
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((0, 0, size - 1, size - 1), fill=(76, 175, 80, 255))
    draw.line(
        [(size * 0.28, size * 0.52), (size * 0.43, size * 0.68), (size * 0.73, size * 0.34)],
        fill="white",
        width=int(size * 0.09),
        joint="curve",
    )
    return image.resize((18, 18), Image.LANCZOS)


class Snackbar(customtkinter.CTkFrame):
    """A transient message that floats at the bottom of its master and auto-hides."""

    def __init__(self, master, duration_ms: int = 3000) -> None:
        super().__init__(master, corner_radius=8, fg_color="#323232")
        self._duration_ms = duration_ms
        self._after_id: str | None = None
        icon = _success_icon()
        self._icon_image = customtkinter.CTkImage(light_image=icon, dark_image=icon, size=(18, 18))
        customtkinter.CTkLabel(self, text="", image=self._icon_image).pack(
            side="left", padx=(16, 6), pady=8
        )
        self._label = customtkinter.CTkLabel(self, text="", text_color="white")
        self._label.pack(side="left", padx=(0, 16), pady=8)

    def show(self, message: str) -> None:
        """Display ``message`` for the configured duration, then hide."""
        self._label.configure(text=message)
        self.place(relx=0.5, rely=1.0, anchor="s", y=-20)
        self.lift()
        if self._after_id is not None:
            self.after_cancel(self._after_id)
        self._after_id = self.after(self._duration_ms, self.hide)

    def hide(self) -> None:
        self._after_id = None
        self.place_forget()


class _IconDialog(customtkinter.CTkToplevel):
    """Base modal toplevel: wears the app icon and grabs focus.

    CTkToplevel resets its icon shortly after creation, so we apply it now and
    reassert it on a short delay.
    """

    def __init__(self, master, title: str, icon_path: str | None = ICON_PATH) -> None:
        super().__init__(master)
        self.title(title)
        self._icon_path = icon_path
        self.transient(master)
        self.after(10, self._grab)
        if icon_path:
            self._apply_icon()
            self.after(300, self._apply_icon)

    def _apply_icon(self) -> None:
        try:
            self.iconbitmap(self._icon_path)
        except (OSError, TclError):
            pass

    def _grab(self) -> None:
        self.grab_set()
        self.lift()
        self.focus_force()


class ConflictDialog(_IconDialog):
    """Modal prompt for resolving a destination name clash.

    ``result`` is one of "rename" (keep both), "skip", or "overwrite". Closing
    the window defaults to "skip".
    """

    def __init__(self, master, filename: str, folder: str, icon_path: str | None = ICON_PATH) -> None:
        super().__init__(master, "File already exists", icon_path)
        self.resizable(False, False)
        self.result = "skip"
        self.grid_columnconfigure((0, 1, 2), weight=1)

        message = f'"{filename}" already exists in {folder}/.\n\nWhat would you like to do?'
        customtkinter.CTkLabel(self, text=message, justify="left", wraplength=380).grid(
            row=0, column=0, columnspan=3, padx=20, pady=(20, 16), sticky="w"
        )
        customtkinter.CTkButton(self, text="Keep both", command=lambda: self._choose("rename")).grid(
            row=1, column=0, padx=(20, 6), pady=(0, 20), sticky="ew"
        )
        customtkinter.CTkButton(self, text="Skip", command=lambda: self._choose("skip")).grid(
            row=1, column=1, padx=6, pady=(0, 20), sticky="ew"
        )
        customtkinter.CTkButton(
            self,
            text="Overwrite",
            fg_color="#b04040",
            hover_color="#922f2f",
            command=lambda: self._choose("overwrite"),
        ).grid(row=1, column=2, padx=(6, 20), pady=(0, 20), sticky="ew")

        self.protocol("WM_DELETE_WINDOW", lambda: self._choose("skip"))

    def _choose(self, value: str) -> None:
        self.result = value
        self.destroy()


_PREVIEW_LIMIT = 50


def _format_plan(result: dict, watched: str, output: str) -> str:
    """Render a dry-run plan as an indented folder/file tree."""
    folders = result.get("folders", [])
    unmatched = result.get("unmatched", [])
    lines = [f"Watched: {watched}", f"Output:  {output}", ""]
    if not folders and not unmatched:
        lines.append("Nothing to organise — no files found in the watched folder.")
        return "\n".join(lines)

    for folder, names in folders:
        lines.append(f"{folder}/  ({len(names)})")
        for name in names[:_PREVIEW_LIMIT]:
            lines.append(f"      {name}")
        if len(names) > _PREVIEW_LIMIT:
            lines.append(f"      … and {len(names) - _PREVIEW_LIMIT} more")
        lines.append("")

    if unmatched:
        lines.append(f"Left in place — no rule matched  ({len(unmatched)})")
        for name in unmatched[:_PREVIEW_LIMIT]:
            lines.append(f"      {name}")
        if len(unmatched) > _PREVIEW_LIMIT:
            lines.append(f"      … and {len(unmatched) - _PREVIEW_LIMIT} more")
        lines.append("")

    lines.append(
        f"{result.get('matched', 0)} file(s) would move into {len(folders)} folder(s); "
        f"{len(unmatched)} left in place."
    )
    if result.get("sorted"):
        lines.append("Sorting is on — files in each folder will also be renumbered (NNN_).")
    return "\n".join(lines)


class UpdateDialog(_IconDialog):
    """Prompt to open the download page when a newer release is available."""

    def __init__(
        self, master, current: str, latest: str, url: str, on_update=None, icon_path=ICON_PATH
    ) -> None:
        super().__init__(master, "Update available", icon_path)
        self.resizable(False, False)
        self._url = url
        self._on_update = on_update
        self.grid_columnconfigure((0, 1), weight=1)

        message = (
            "A new version of File Organiser is available.\n\n"
            f"You have:  v{current}\nLatest:      v{latest}"
        )
        customtkinter.CTkLabel(self, text=message, justify="left").grid(
            row=0, column=0, columnspan=2, padx=20, pady=(20, 16), sticky="w"
        )
        customtkinter.CTkButton(self, text="Update", command=self._update).grid(
            row=1, column=0, padx=(20, 6), pady=(0, 20), sticky="ew"
        )
        customtkinter.CTkButton(
            self, text="Cancel", fg_color="gray40", hover_color="gray30", command=self.destroy
        ).grid(row=1, column=1, padx=(6, 20), pady=(0, 20), sticky="ew")

    def _update(self) -> None:
        webbrowser.open(self._url)
        self.destroy()
        if self._on_update is not None:
            self._on_update()


class SimulationDialog(_IconDialog):
    """Read-only preview of what organising would do — a dry run."""

    def __init__(self, master, result: dict, watched: str, output: str, icon_path=ICON_PATH) -> None:
        super().__init__(master, "Dry run — preview", icon_path)
        self.geometry("560x600")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        box = customtkinter.CTkTextbox(self, wrap="none")
        box.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        box.insert("1.0", _format_plan(result, watched, output))
        box.configure(state="disabled")

        customtkinter.CTkButton(self, text="Close", width=100, command=self.destroy).grid(
            row=1, column=0, pady=(0, 12)
        )
