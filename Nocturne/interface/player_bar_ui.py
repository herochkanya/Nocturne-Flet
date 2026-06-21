import flet as ft
import asyncio
import inspect

class AppPlayerBar(ft.Container):
    def __init__(self, backend, layout_style):
        super().__init__(height=90, padding=20, bgcolor="surfacevariant")
        self.backend = backend
        self.layout_style = layout_style

        self._is_seeking = False
        self._is_changing_track = False
        self._current_load_task = None

        # --- TRACK INFO (Твій оригінальний UI) ---
        self.cover_img = ft.Image(
            src="", width=50, height=50, border_radius=8,
            fit="cover", visible=False, gapless_playback=True
        )
        self.placeholder = ft.Container(
            width=50, height=50, bgcolor="white10", border_radius=8,
            content=ft.Icon(ft.Icons.MUSIC_NOTE, color="white24"),
            visible=True
        )

        self.title_text = ft.Text(
            value="Welcome to Nocturne", weight="bold", 
            size=14, color="white", no_wrap=True, animate_opacity=200 
        )
        self.artist_text = ft.Text("", size=12, color="white60", no_wrap=True)

        self.track_details_clicker = ft.Container(
            content=ft.Column([
                self.title_text,
                self.artist_text,
            ], spacing=0, alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.Padding(left=10, right=10),
            on_click=self._go_to_current_track,
            on_hover=self._handle_title_hover,
            bgcolor=ft.Colors.TRANSPARENT 
        )
        
        self.track_info = ft.Row([
            ft.Stack([self.placeholder, self.cover_img]),
            self.track_details_clicker 
        ], spacing=15, expand=2)

        # --- CONTROLS ---
        self.play_btn = ft.Container(
            width=35, height=35, bgcolor="white", border_radius=20,
            content=ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED, size=30, color="black"),
            on_click=self._toggle_play_internal
        )

        self.shuffle_btn = ft.IconButton(
            ft.Icons.SHUFFLE, icon_size=18, icon_color="white30",
            on_click=self._toggle_shuffle_ui
        )

        self.repeat_btn = ft.IconButton(
            ft.Icons.REPEAT, icon_size=18, icon_color="white30",
            on_click=self._toggle_cycle_ui
        )

        self.slider = ft.Slider(
            min=0, max=1, value=0, expand=True, margin=0, padding=0,
            active_color="white", inactive_color="white12",
            on_change_start=self._on_slider_start,
            on_change_end=self._on_slider_change,
        )

        self.time_now = ft.Text("0:00", size=11, color="white60", width=40)
        self.time_total = ft.Text("0:00", size=11, color="white60", width=40, text_align="right")

        self.main_controls = ft.Column([
            ft.Row([
                self.shuffle_btn,
                ft.IconButton(ft.Icons.SKIP_PREVIOUS_ROUNDED, 
                            on_click=lambda _: self.page.run_task(self._safe_action, "prev_track")),
                self.play_btn,
                ft.IconButton(ft.Icons.SKIP_NEXT_ROUNDED, 
                            on_click=lambda _: self.page.run_task(self._safe_action, "next_track")),
                self.repeat_btn,
            ], alignment="center", spacing=10),
            ft.Row([self.time_now, self.slider, self.time_total], alignment="center", spacing=0, margin=5)
        ], expand=4, spacing=0, margin=ft.Margin(top=-10))

        # --- VOLUME & EXTRA ---
        self.volume_slider = ft.Slider(
            min=0, max=100, value=70, width=80, padding=0, margin=0,
            active_color="white", on_change=self._on_volume_change
        )

        self.extra_controls = ft.Row([
            ft.IconButton(ft.Icons.PLAYLIST_PLAY, icon_size=20, icon_color="white60"),
            ft.Icon(ft.Icons.VOLUME_UP_ROUNDED, size=18, color="white60"),
            self.volume_slider,
        ], expand=2, alignment="end", spacing=5)

        self.content = ft.Row([
            self.track_info,
            self.main_controls,
            self.extra_controls
        ], alignment="center", vertical_alignment="center", spacing=10, expand=True)

    # --- LOGIC ---

    def _format_time(self, seconds):
        """Метод повернуто для усунення AttributeError."""
        if not seconds or seconds < 0: return "0:00"
        m, s = divmod(int(seconds), 60)
        return f"{m}:{s:02d}"

    async def update_track(self, track_data):
        if not track_data: return
        if self._current_load_task and not self._current_load_task.done():
            self._current_load_task.cancel()
        self._current_load_task = asyncio.create_task(self._do_update_ui(track_data))

    async def _do_update_ui(self, track_data):
        try:
            self._is_changing_track = True
            duration = float(track_data.get("duration") or 0)
            self.slider.max = duration if duration > 0 else 1.0
            self.slider.value = 0
            
            self.time_total.value = self._format_time(duration)
            self.time_now.value = "0:00"
            self.title_text.value = track_data.get("title", "Unknown")
            self.artist_text.value = track_data.get("artist", "Unknown Artist")
            
            ui_cover = track_data.get("thumbnail_url")
            self.cover_img.src = ui_cover
            self.cover_img.visible = bool(ui_cover)
            self.placeholder.visible = not bool(ui_cover)

            self.update_state_ui(True) # Оновлюємо іконку паузи
            await asyncio.sleep(0.1) 
            self._is_changing_track = False
        except asyncio.CancelledError: pass
        except Exception as e: print(f"Error: {e}")

    def update_progress(self, current):
        if self._is_changing_track or self._is_seeking: return
        try:
            curr_val = float(current)
            self.slider.value = curr_val
            self.time_now.value = self._format_time(curr_val)
            self.slider.update()
            self.time_now.update()
        except: pass

    def update_state_ui(self, is_playing=None):
        """Синхронізація станів кнопок."""
        playing = is_playing if is_playing is not None else self.backend.is_playing
        self.play_btn.content.icon = ft.Icons.PAUSE_ROUNDED if playing else ft.Icons.PLAY_ARROW_ROUNDED
        
        # Shuffle/Repeat
        is_shuffled = getattr(self.backend, "shuffle_enabled", False)
        self.shuffle_btn.icon_color = "white" if is_shuffled else "white30"
        
        mode = getattr(self.backend, "_cycle_mode", 0)
        mode_configs = {
            0: (ft.Icons.REPEAT, "white30"),
            1: (ft.Icons.REPEAT, "white"),
            2: (ft.Icons.REPEAT_ONE, "white")
        }
        self.repeat_btn.icon, self.repeat_btn.icon_color = mode_configs.get(mode, (ft.Icons.REPEAT, "white30"))
        
        try: self.update()
        except: pass

    # --- HANDLERS (Твої оригінальні) ---

    def _on_slider_start(self, e): self._is_seeking = True

    def _on_slider_change(self, e):
        self.backend.seek(float(e.control.value))
        self._is_seeking = False
    
    def _on_volume_change(self, e):
        self.backend.set_volume(e.control.value / 100)

    def _toggle_play_internal(self, e):
        self.backend.toggle_pause()
        self.update_state_ui()

    async def _safe_action(self, method_name):
        if self._is_changing_track and method_name in ["next_track", "prev_track"]: return
        method = getattr(self.backend, method_name)
        if inspect.iscoroutinefunction(method): await method()
        else: await asyncio.get_running_loop().run_in_executor(None, method)
        self.update_state_ui()

    def _toggle_shuffle_ui(self, e):
        self.backend.toggle_shuffle()
        self.update_state_ui()

    def _toggle_cycle_ui(self, e):
        curr = getattr(self.backend, "_cycle_mode", 0)
        self.backend.set_cycle_mode((curr + 1) % 3)
        self.update_state_ui()

    async def _go_to_current_track(self, e):
        if not self.backend.current_track or self.layout_style == "modern": return
        if hasattr(self.page, "change_screen"): await self.page.change_screen("player")
        self.page.pubsub.send_all_on_topic("player_scroll", self.backend.current_track.path)
    
    def _handle_title_hover(self, e):
        # Використовуємо твою логіку кольорів
        is_now_white = self.title_text.color == ft.Colors.WHITE or self.title_text.color == "white"
        self.title_text.color = ft.Colors.BLUE_400 if is_now_white else ft.Colors.WHITE
        self.title_text.decoration = ft.TextDecoration.UNDERLINE if is_now_white else ft.TextDecoration.NONE
        try: self.title_text.update()
        except: pass