"""Main window and tab wiring."""
import logging
import queue
import threading
from pathlib import Path
from tkinter import messagebox

import customtkinter
import yaml

from src.config.config_manager import import_config, load_config, save_user_config
from src.config.rules import RulesConfig
from src.gui.control_tab import ControlTab
from src.gui.logs_tab import LogsTab
from src.gui.rules_tab import RulesTab
from src.gui.tray import TRAY_AVAILABLE, TrayIcon
from src.gui.widgets import ICON_PATH, ConflictDialog, Snackbar
from src.service.service import OrganiserService
from src.utils import autostart


class App(customtkinter.CTk):
    """The File Organiser desktop window."""

    def __init__(self, start_hidden: bool = False) -> None:
        super().__init__()
        self._alive = True
        self._hidden = False
        self._tray: TrayIcon | None = None
        self._pending_queue: queue.Queue = queue.Queue()
        self._conflict_queue: queue.Queue = queue.Queue()
        self._activate_queue: queue.Queue = queue.Queue()
        self.report_callback_exception = self._on_gui_error

        self.title("File organiser")
        self.iconbitmap(ICON_PATH)
        self.geometry("640x760")

        self._config = load_config()
        self.service = OrganiserService(rules=self._config)
        self.service.conflict_resolver = self._resolve_conflict

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        tabview = customtkinter.CTkTabview(master=self)
        tabview.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        self._rules_frame = tabview.add("Rules")
        control_tab = tabview.add("Control")
        logs_tab = tabview.add("Logs")

        self._snackbar = Snackbar(self)

        control_tab.grid_columnconfigure(0, weight=1)
        self._control = ControlTab(control_tab, self.service)
        self._control.grid(row=0, column=0, sticky="ew")

        logs_tab.grid_columnconfigure(0, weight=1)
        logs_tab.grid_rowconfigure(0, weight=1)
        LogsTab(logs_tab, self.service).grid(row=0, column=0, sticky="nsew")

        self._rules_frame.grid_columnconfigure(0, weight=1)
        self._rules_frame.grid_rowconfigure(0, weight=1)
        self._rules_view: RulesTab | None = None
        self._build_rules_view()

        # background mode: start watching without waiting for a manual Start
        watch = self._config.watch
        if (start_hidden or autostart.is_enabled()) and watch.directory and watch.output:
            self.service.start()
            self._control.refresh()

        # resolve visible conflicts on the GUI thread (Tkinter is single-threaded)
        self.after(100, self._poll_conflicts)
        self.after(150, self._poll_activate)

        # close hides to the tray; Quit exits
        self._tray_queue: queue.Queue = queue.Queue()
        if TRAY_AVAILABLE:
            self._tray = TrayIcon(
                ICON_PATH,
                on_open=lambda: self._tray_queue.put("open"),
                on_quit=lambda: self._tray_queue.put("quit"),
            )
            self._tray.start()
            self.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
            self.after(200, self._poll_tray)
            if start_hidden:
                self.withdraw()
                self._hidden = True

    def _build_rules_view(self) -> None:
        """(Re)create the Rules tab from the current config (e.g. after import)."""
        if self._rules_view is not None:
            self._rules_view.destroy()
        self._rules_view = RulesTab(
            self._rules_frame,
            self._config,
            on_save=self._save_rules,
            on_import=self._import_rules,
            notify=self._snackbar.show,
        )
        self._rules_view.grid(row=0, column=0, sticky="nsew")

    def _resolve_conflict(self, source: Path, target: Path) -> str:
        """Decide a name-clash outcome: defer + notify when hidden, else prompt."""
        if self._hidden:
            self._pending_queue.put((source, target))
            if self._tray is not None:
                self._tray.notify(
                    f'"{target.name}" needs a decision. Open File organiser to choose.',
                    "File organiser — conflict",
                )
            return "defer"
        if threading.current_thread() is threading.main_thread():
            return self._conflict_dialog(target)
        holder: dict[str, str] = {}
        answered = threading.Event()
        self._conflict_queue.put((target, holder, answered))
        answered.wait()
        return holder.get("value", "skip")

    def _poll_conflicts(self) -> None:
        if not self._alive:
            return
        try:
            while True:
                target, holder, answered = self._conflict_queue.get_nowait()
                holder["value"] = self._conflict_dialog(target)
                answered.set()
        except queue.Empty:
            pass
        self.after(100, self._poll_conflicts)

    def _conflict_dialog(self, target: Path) -> str:
        dialog = ConflictDialog(self, target.name, target.parent.name, icon_path=ICON_PATH)
        self.wait_window(dialog)
        return dialog.result

    def _process_pending_conflicts(self) -> None:
        """Resolve clashes that were deferred while the app was hidden."""
        try:
            while True:
                source, target = self._pending_queue.get_nowait()
                if not source.exists():
                    continue
                decision = self._conflict_dialog(target)
                self.service.organise_with_decision(source, decision)
        except queue.Empty:
            pass

    def request_show(self, *_args) -> None:
        """Thread-safe request to surface the window (from the single-instance server)."""
        self._activate_queue.put(True)

    def _poll_activate(self) -> None:
        if not self._alive:
            return
        try:
            while True:
                self._activate_queue.get_nowait()
                self._show_window()
        except queue.Empty:
            pass
        self.after(150, self._poll_activate)

    def _on_gui_error(self, exc, val, tb) -> None:
        """Log an unhandled GUI-callback error and show a dialog instead of dying."""
        logging.getLogger("src").error("GUI error", exc_info=(exc, val, tb))
        try:
            messagebox.showerror("File organiser", f"An unexpected error occurred:\n{val}")
        except Exception:  # never let the error reporter crash the app
            pass

    def _hide_to_tray(self) -> None:
        """Closing the window hides it; the watcher keeps running."""
        self.withdraw()
        self._hidden = True

    def _show_window(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()
        self._hidden = False
        self._process_pending_conflicts()

    def _quit(self) -> None:
        self._alive = False
        try:
            self.service.stop()
        finally:
            if self._tray is not None:
                self._tray.stop()
            self.destroy()

    def _poll_tray(self) -> None:
        if not self._alive:
            return
        try:
            while True:
                action = self._tray_queue.get_nowait()
                if action == "open":
                    self._show_window()
                elif action == "quit":
                    self._quit()
                    return
        except queue.Empty:
            pass
        self.after(200, self._poll_tray)

    def _save_rules(self, config: RulesConfig) -> None:
        """Persist edited rules and apply them to the (possibly running) service."""
        save_user_config(config)
        self._config = config
        self.service.rules = config
        if self.service.is_running:
            self.service.stop()
            self.service.start()
        self._control.refresh()
        self._snackbar.show("Rules saved successfully")

    def _import_rules(self, path: str) -> None:
        """Replace the rules from an imported file, keeping this device's folders."""
        try:
            imported = import_config(path)
        except (OSError, yaml.YAMLError):
            messagebox.showerror("Import failed", "That file could not be read as a rules config.")
            return
        self._config.format_rules = imported.format_rules
        self._config.sort = imported.sort
        save_user_config(self._config)
        self.service.rules = self._config
        if self.service.is_running:
            self.service.stop()
            self.service.start()
        self._build_rules_view()
        self._control.refresh()
        self._snackbar.show("Rules imported")
