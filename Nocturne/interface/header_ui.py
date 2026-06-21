# interface/header_ui.py

import flet as ft, os, subprocess

class AppHeader(ft.Container):

    # --- UI ---

    def __init__(self, page: ft.Page, on_screen_change, on_back, on_forward):
        super().__init__(height = 55, bgcolor = "surfacevariant")
        self.header_page = page
        self.on_screen_change = on_screen_change 
        self.on_back = on_back
        self.on_forward = on_forward
        
        # --- RIGHT ---
        self.back_btn = ft.IconButton(
            ft.Icons.CHEVRON_LEFT_ROUNDED, 
            icon_size=22,
            disabled=True,
            on_click=lambda _: self.header_page.run_task(self.on_back)
        )
        self.forward_btn = ft.IconButton(
            ft.Icons.CHEVRON_RIGHT_ROUNDED, 
            icon_size=22, 
            disabled=True,
            on_click=lambda _: self.header_page.run_task(self.on_forward)
        )

        self.nav_group = ft.Row([
            ft.TextButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.DOWNLOAD_FOR_OFFLINE, size=20),
                    ft.Text("Downloader", size=13, weight="w500"),
                ], spacing=5),
                on_click=lambda _: self._handle_nav("downloader")
            ),
            self.back_btn,
            self.forward_btn,
        ], expand=1, width=250, spacing=0)

        # --- LEFT ---
        self.window_controls = ft.Row([
            ft.IconButton(
                ft.Icons.SETTINGS_OUTLINED, 
                icon_size=20,
                margin=ft.Margin(right=20),
                on_click=lambda _: self._handle_nav("settings")
            ),

            ft.TextButton(
                content=ft.Icon(ft.Icons.REMOVE, size=16, color="white"),
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=0),
                    overlay_color={"": ft.Colors.with_opacity(0.1, "white")},
                ),
                width=45, height=55,
                on_click=self.minimize_window,
            ),
            ft.TextButton(
                content=ft.Icon(ft.Icons.CROP_SQUARE, size=14, color="white"),
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=0),
                    overlay_color={"": ft.Colors.with_opacity(0.1, "white")},
                ),
                width=45, height=55,
                on_click=self.toggle_maximize,
            ),
            ft.TextButton(
                content=ft.Icon(ft.Icons.CLOSE, size=16, color="white"),
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=0),
                    overlay_color={"": "red700"}, 
                ),
                width=45, height=55,
                on_click=self.close_window,
            ),
        ], expand=1, width=220, spacing=0, alignment=ft.MainAxisAlignment.END)

        # --- CENTER & MAIN ASSEMBLY ---
        self.content = ft.WindowDragArea(
            content=ft.Row([
                self.nav_group,
                ft.Row([
                    ft.IconButton(
                        ft.Icons.HOME_ROUNDED, 
                        icon_size=24, 
                        bgcolor="grey900",
                        on_click=lambda _: self._handle_nav("player")
                    ),
                    ft.TextField(
                        hint_text="Search tracks...",
                        height=35, expand=True, border_radius=20, filled=True,
                        bgcolor="grey900", border_color="transparent",
                        content_padding=ft.Padding(left=15, bottom=12),
                        text_size=13,
                    )
                ], expand=True, alignment="center", spacing=10),
                self.window_controls
            ], alignment="center", vertical_alignment="center", spacing=20, expand=True)
        )

    # --- HANDLERS ---

    def _handle_nav(self, screen_name):
        # Dispatches screen change event to the main controller.
        if self.on_screen_change:
            self.header_page.run_task(self.on_screen_change, screen_name)

    def minimize_window(self, e):
        self.header_page.window.minimized = True
        self.header_page.update()

    def toggle_maximize(self, e):
        self.header_page.window.maximized = not self.header_page.window.maximized
        self.header_page.update()

    def close_window(self, e):
        pid = os.getpid()
        try:
            # Using taskkill on Windows to ensure a deep cleanup of resources
            subprocess.Popen(
                f"taskkill /F /T /PID {pid}", 
                shell=True, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
        except Exception:
            # Fallback for non-Windows environments or permission issues
            os._exit(0)