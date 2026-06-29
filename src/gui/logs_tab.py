"""Logs tab: a live view of activity in the watched directory."""
import logging
import queue

import customtkinter

from src.service.service import OrganiserService


def _human_size(num: int) -> str:
    size = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _format_stats(moved: int, total_size: int, per_category: dict[str, int]) -> str:
    if moved == 0:
        return "No files organised yet."
    plural = "s" if moved != 1 else ""
    counts = " · ".join(
        f"{name} {count}"
        for name, count in sorted(per_category.items(), key=lambda kv: (-kv[1], kv[0]))
    )
    return f"Moved {moved} file{plural} · {_human_size(total_size)}\n{counts}"


class _QueueHandler(logging.Handler):
    """A logging handler that just forwards formatted lines to a queue."""

    def __init__(self, log_queue: "queue.Queue[str]") -> None:
        super().__init__()
        self._queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        self._queue.put(self.format(record))


class LogsTab(customtkinter.CTkFrame):
    """Shows the watched folders and a running log of every operation."""

    def __init__(self, master, service: OrganiserService) -> None:
        super().__init__(master, fg_color="transparent")
        self._service = service
        self._queue: "queue.Queue[str]" = queue.Queue()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._stats_label = customtkinter.CTkLabel(
            self, text="", anchor="w", justify="left", font=customtkinter.CTkFont(weight="bold")
        )
        self._stats_label.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 2))

        self._header = customtkinter.CTkLabel(self, text="", anchor="w", justify="left")
        self._header.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 4))

        self._box = customtkinter.CTkTextbox(self, wrap="none")
        self._box.grid(row=2, column=0, sticky="nsew", padx=10, pady=4)
        self._box.configure(state="disabled")

        customtkinter.CTkButton(self, text="Clear", width=80, command=self._clear).grid(
            row=3, column=0, sticky="e", padx=10, pady=(0, 10)
        )

        handler = _QueueHandler(self._queue)
        handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))
        src_logger = logging.getLogger("src")
        src_logger.setLevel(logging.INFO)
        for existing in [h for h in src_logger.handlers if isinstance(h, _QueueHandler)]:
            src_logger.removeHandler(existing)  # avoid stacking across window re-creations
        src_logger.addHandler(handler)

        self._poll()

    def _clear(self) -> None:
        self._box.configure(state="normal")
        self._box.delete("1.0", "end")
        self._box.configure(state="disabled")

    def _poll(self) -> None:
        watch = self._service.rules.watch
        self._header.configure(
            text=f"Watching: {watch.directory or '(not set)'}\nOutput:   {watch.output or '(not set)'}"
        )
        self._stats_label.configure(text=_format_stats(*self._service.stats.snapshot()))
        lines = []
        try:
            while True:
                lines.append(self._queue.get_nowait())
        except queue.Empty:
            pass
        if lines:
            self._box.configure(state="normal")
            self._box.insert("end", "\n".join(lines) + "\n")
            self._box.see("end")
            self._box.configure(state="disabled")
        self.after(400, self._poll)
