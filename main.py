# import logging
# import sys
#
# from watchdog.observers import Observer
# from watchdog.events import LoggingEventHandler
import customtkinter
from customtkinter import CTkFont

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("File organiser")
        self.iconbitmap('./assets/icons/folder.ico')
        self.geometry("400x600")

        self.grid_columnconfigure(0, weight=1)
        # label = customtkinter.CTkLabel(self, text="File Organiser", font=(CTkFont, 40), fg_color="transparent")
        # label.grid(row=0, column=0, padx=20, pady=20)

        tabview = customtkinter.CTkTabview(master=self)
        tabview.pack(padx=20, pady=20)

        rules_tab = tabview.add("Rules")
        control_tab = tabview.add("Control")
        logs_tab = tabview.add("Logs")

        # Rules tab
        label = customtkinter.CTkLabel(master=rules_tab, text="Define organisation rules", font=(CTkFont, 20), fg_color="transparent")
        label.grid(row=0, column=0, padx=20, pady=20)

        # Control tab

        # Logs tab

        #
        # start_btn = customtkinter.CTkButton(self, text="Start", command=self.start_btn_callback)
        # start_btn.grid(row=1, column=0, padx=20, pady=20, sticky="ew")
        #
        # pause_btn = customtkinter.CTkButton(self, text="Pause", command=self.pause_btn_callback)
        # pause_btn.grid(row=2, column=0, padx=20, pady=20, sticky="ew")
        #
        # stop_btn = customtkinter.CTkButton(self, text="Stop", command=self.stop_btn_callback)
        # stop_btn.grid(row=3, column=0, padx=20, pady=20, sticky="ew")

    def start_btn_callback(self):
        print("start btn pressed")

    def pause_btn_callback(self):
        print("pause btn pressed")

    def stop_btn_callback(self):
        print("stop btn pressed")

if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO,
    #                     format='%(asctime)s - %(message)s',
    #                     datefmt='%Y-%m-%d %H:%M:%S')
    # path = sys.argv[1] if len(sys.argv) > 1 else '.'
    # event_handler = LoggingEventHandler()
    # observer = Observer()
    # observer.schedule(event_handler, path, recursive=True)
    # observer.start()
    # try:
    #     while observer.is_alive():
    #         observer.join(1)
    # finally:
    #     observer.stop()
    #     observer.join()
    app = App()
    app.mainloop()