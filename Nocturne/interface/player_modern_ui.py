import flet as ft

class PlayerModernScreen(ft.Container):
    def __init__(self, backend):
        super().__init__(visible=True, expand=True, padding=20, border_radius = 10)
        self.backend = backend
        self.margin = ft.Margin.symmetric(horizontal=10)

        self.bgcolor = "#161616"
    
    async def initial_sync(self):
        pass

    async def cleanup(self):
        pass

    def did_mount(self):
        if self.page:
            self.page.run_task(self.initial_sync)
