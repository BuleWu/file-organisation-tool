"""Control tab: start/pause/stop the watcher and show its status."""
import customtkinter

from src.gui.widgets import SimulationDialog
from src.service.service import OrganiserService
from src.utils import autostart


class ControlTab(customtkinter.CTkFrame):
    """Buttons that drive the OrganiserService, plus a status line."""

    def __init__(self, master, service: OrganiserService) -> None:
        super().__init__(master, fg_color="transparent")
        self._service = service
        self.grid_columnconfigure((0, 1, 2), weight=1)

        customtkinter.CTkButton(self, text="Start", command=self._start).grid(
            row=0, column=0, padx=10, pady=10, sticky="ew"
        )
        customtkinter.CTkButton(self, text="Pause", command=self._pause).grid(
            row=0, column=1, padx=10, pady=10, sticky="ew"
        )
        customtkinter.CTkButton(self, text="Stop", command=self._stop).grid(
            row=0, column=2, padx=10, pady=10, sticky="ew"
        )

        customtkinter.CTkButton(
            self, text="Organise existing files now", command=self._organise_existing
        ).grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="ew")

        customtkinter.CTkButton(
            self, text="Simulate (dry run)", command=self._simulate
        ).grid(row=2, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="ew")

        self._autostart = customtkinter.CTkSwitch(
            self, text="Run on Windows startup", command=self._toggle_autostart
        )
        self._autostart.grid(row=3, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="w")
        if autostart.is_enabled():
            self._autostart.select()
        if not autostart.is_supported():
            self._autostart.configure(state="disabled", text="Run on Windows startup (Windows only)")

        self._status = customtkinter.CTkLabel(self, text="", anchor="w", justify="left")
        self._status.grid(row=4, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="ew")
        self.refresh()

    def _start(self) -> None:
        self._service.start()
        self.refresh()

    def _pause(self) -> None:
        self._service.pause()
        self.refresh()

    def _stop(self) -> None:
        self._service.stop()
        self.refresh()

    def _organise_existing(self) -> None:
        watch = self._service.rules.watch
        if not watch.directory or not watch.output:
            self._status.configure(
                text="Set a watched folder and an output folder in the Rules tab.",
                text_color="#e0a030",
            )
            return
        count = self._service.organise_existing()
        self._status.configure(text=f"Organised {count} existing file(s).", text_color="#4caf50")

    def _toggle_autostart(self) -> None:
        if self._autostart.get():
            autostart.enable()
        else:
            autostart.disable()

    def _simulate(self) -> None:
        watch = self._service.rules.watch
        if not watch.directory or not watch.output:
            self._status.configure(
                text="Set a watched folder and an output folder in the Rules tab.",
                text_color="#e0a030",
            )
            return
        result = self._service.simulate()
        SimulationDialog(self.winfo_toplevel(), result, watch.directory, watch.output)

    def refresh(self) -> None:
        """Update the status line from the service and the current rules."""
        watch = self._service.rules.watch
        if self._service.is_running:
            text, color = f"Watching {watch.directory}\n→ {watch.output}", "#4caf50"
        elif not watch.directory or not watch.output:
            text, color = "Set a watched folder and an output folder in the Rules tab.", "#e0a030"
        else:
            text, color = "Stopped.", "gray"
        self._status.configure(text=text, text_color=color)
