import flet as ft

class SettingsScreen(ft.Container):
    def __init__(self):
        super().__init__(visible=False, expand=True, padding=20, border_radius = 10)
        self.margin = ft.Margin.symmetric(horizontal=10)

        self.bgcolor = "#161616"