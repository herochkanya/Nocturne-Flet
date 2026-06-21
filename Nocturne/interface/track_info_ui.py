import flet as ft

class TrackDetails(ft.Container):
    def __init__(self):
        # --- CONFIGURATION ---
        self.collapsed_width = 60
        self.expanded_width = 360 # Фіксована ширина для відкритого стану
        self.is_expanded = False
        
        # English comments as requested
        # Smooth decelerate animation for state switching
        self.standard_anim = ft.Animation(400, ft.AnimationCurve.DECELERATE)

        super().__init__(
            width=self.collapsed_width,
            padding=0, 
            border_radius=10,
            bgcolor="#161616",
            animate=self.standard_anim,
            clip_behavior=ft.ClipBehavior.HARD_EDGE # Prevents content overflow during animation
        )

        # 1. TOGGLE BUTTON
        self.toggle_btn = ft.IconButton(
            icon=ft.Icons.KEYBOARD_ARROW_LEFT_ROUNDED,
            icon_color="white70",
            on_click=self.toggle_state,
            tooltip="Розгорнути"
        )

        self.playlist_title = ft.Text("Playlist", weight="bold", size=11, color="white54"), 

        # 2. MAIN CONTENT
        self.details_content = ft.Column([
            ft.Container(
                aspect_ratio=1,
                expand=True, 
                bgcolor="white10", border_radius=12,
                alignment=ft.Alignment(0, 0),
                content=ft.Icon(ft.Icons.MUSIC_NOTE_ROUNDED, size=80, color="white24")
            ),
            ft.Column([
                ft.Text("Назва треку", size=22, weight="bold", no_wrap=True),
                ft.Text("Виконавець", color="white60", size=16, no_wrap=True),
            ], spacing=4),
        ], 
        visible=False, 
        spacing=25,
        )

        # 3. LAYOUT ASSEMBLY
        self.content = ft.Container(
            padding=ft.Padding(top=10, bottom=20, left=10, right=10),
            content=ft.Column([
                ft.Container(
                    content=self.toggle_btn, 
                    alignment=ft.Alignment(-1, 0)
                ),
                self.details_content
            ], horizontal_alignment=ft.CrossAxisAlignment.START)
        )

    def toggle_state(self, e=None, force_close=False):
        # Logic for force closing from main.py
        if force_close:
            self.is_expanded = False
        else:
            self.is_expanded = not self.is_expanded
        
        # Call the manager to check if the left panel should be closed
        if self.is_expanded and hasattr(self, 'on_toggle') and self.on_toggle:
            self.on_toggle()

        if self.is_expanded:
            self.width = self.expanded_width
            self.toggle_btn.icon = ft.Icons.KEYBOARD_ARROW_RIGHT_ROUNDED
            self.toggle_btn.tooltip = "Згорнути"
            self.details_content.visible = True
            self.details_content.opacity = 1
        else:
            self.width = self.collapsed_width
            self.toggle_btn.icon = ft.Icons.KEYBOARD_ARROW_LEFT_ROUNDED
            self.toggle_btn.tooltip = "Розгорнути"
            self.details_content.visible = False
            self.details_content.opacity = 0
            
        self.update()