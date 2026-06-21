import flet as ft

class PlaylistNavigation(ft.Container):
    def __init__(self, toggle_others_callback=None):
        super().__init__()
        # --- CONFIGURATION ---
        self.collapsed_width = 60
        self.expanded_width = 280
        self.is_expanded = False
        self.toggle_others_callback = toggle_others_callback # For exclusive mode

        self.width = self.collapsed_width
        self.bgcolor = "#161616"
        self.border_radius = 10
        self.padding = 10
        self.animate = ft.Animation(400, ft.AnimationCurve.DECELERATE)
        self.clip_behavior = ft.ClipBehavior.HARD_EDGE
        self.margin = ft.Margin(left=10)

        # Toggle Button (Menu icon)
        self.toggle_btn = ft.IconButton(
            icon=ft.Icons.MENU_ROUNDED,
            icon_color="white70",
            on_click=self.toggle_state
        )

        # Playlist Content (Example)
        self.nav_content = ft.Column([
            ft.Text("МЕДІАТЕКА", weight="bold", size=12, color="white54"),
            ft.ListTile(leading=ft.Icon(ft.Icons.FAVORITE_ROUNDED), title=ft.Text("Улюблені")),
            ft.ListTile(leading=ft.Icon(ft.Icons.QUEUE_MUSIC_ROUNDED), title=ft.Text("Плейлисти")),
            ft.ListTile(leading=ft.Icon(ft.Icons.HISTORY_ROUNDED), title=ft.Text("Нещодавні")),
        ], visible=False, opacity=0, spacing=10)

        self.content = ft.Column([
            ft.Container(content=self.toggle_btn, alignment=ft.Alignment(-1, 0)),
            ft.Divider(height=10, color="transparent"),
            self.nav_content
        ])

    def toggle_state(self, e=None, force_close=False):
        if force_close:
            self.is_expanded = False
        else:
            self.is_expanded = not self.is_expanded

        # Call the manager to check if the right panel should be closed
        if self.is_expanded and hasattr(self, 'on_toggle') and self.on_toggle:
            self.on_toggle()

        if self.is_expanded:
            self.width = self.expanded_width
            self.toggle_btn.icon = ft.Icons.MENU_OPEN_ROUNDED # Or your chosen icon
            # self.toggle_btn.tooltip = "Згорнути"
            self.nav_content.visible = True
            self.nav_content.opacity = 1
        else:
            self.width = self.collapsed_width
            self.toggle_btn.icon = ft.Icons.MENU_ROUNDED
            # self.toggle_btn.tooltip = "Розгорнути"
            self.nav_content.visible = False
            self.nav_content.opacity = 0
            
        self.update()