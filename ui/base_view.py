import customtkinter as ctk
from config import APP_BG


class BaseView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=APP_BG, corner_radius=0, **kwargs)
        self.pack(fill="both", expand=True)
