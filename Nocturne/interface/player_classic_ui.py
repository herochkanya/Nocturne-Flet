# interface/player_classic_ui.py

import flet as ft
import asyncio
from core.database import get_sort_setting, set_sort_setting

class PlayerScreen(ft.Container):
    def __init__(self, backend, on_change_screen=None):
        super().__init__(visible=True, expand=True, padding=20, border_radius=10)
        self.backend = backend
        self.margin = ft.Margin.symmetric(horizontal=10)
        self.bgcolor = "#161616"
        self.on_change_screen = on_change_screen
        
        # --- STATE MANAGEMENT ---
        self.all_tracks_data = [] 
        self.visible_count = 10
        self._on_track_select_index = None
        self._is_loading_now = False
        self.render_lock = asyncio.Lock()
        self.current_playlist_name = "GLOBAL PLAYLIST"
        
        self.sort_criterion = get_sort_setting()

        self.playlist_title = ft.Text(
            self.current_playlist_name, 
            size=16, 
            weight="w600", 
            color="white",
            opacity=0.9, 
            font_family="Verdana"
        )
        self.sort_labels = {
            "alphabet": "Alphabet (A-Z)",
            "views": "Popularity",
            "date": "Release Date"
        }
        self.sort_text = ft.Text(self.sort_labels[self.sort_criterion], size=11, color="white70")

        # Кнопка сортування (Тепер просто декоративна)
        self.sort_button = ft.PopupMenuButton(
            content=ft.Row([
                ft.Column([
                    ft.Text("SORT BY", size=9, color="white30", weight="bold"),
                    self.sort_text,
                ], spacing=0, alignment=ft.MainAxisAlignment.CENTER),
                ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, color="white30", size=18)
            ], spacing=8),
            items=[
                ft.PopupMenuItem(
                    content=ft.Text("Alphabet (A-Z)", size=13), 
                    on_click=lambda _: self.page.run_task(self._apply_sort, "alphabet")
                ),
                ft.PopupMenuItem(
                    content=ft.Text("Popularity (Views)", size=13), 
                    on_click=lambda _: self.page.run_task(self._apply_sort, "views")
                ),
                ft.PopupMenuItem(
                    content=ft.Text("Release Date", size=13), 
                    on_click=lambda _: self.page.run_task(self._apply_sort, "date")
                ),
            ]
        )

        self.track_header_controls = ft.Row([
            self.playlist_title,
            self.sort_button
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        self.track_list = ft.Column(
            expand=True, spacing=0, scroll=ft.ScrollMode.AUTO
        )

        self.load_more_btn = ft.Container(
            content=ft.Text("LOAD MORE", size=12, weight="bold", color="blueaccent"),
            alignment=ft.alignment.Alignment(0,0),
            padding=15,
            width=200,
            border_radius=10,
            on_click=self._handle_load_more_click,
            visible=False
        )
        
        self.loader = ft.Container(
            content=ft.ProgressRing(width=20, height=20, stroke_width=2, color="blueaccent"),
            alignment=ft.alignment.Alignment(0,0),
            height=40,
            visible=False
        )

        self.track_list_panel = ft.Container(
            content=ft.Column([
                self.track_list,
                ft.Row([self.load_more_btn], alignment=ft.MainAxisAlignment.CENTER),
                self.loader 
            ], spacing=10, scroll=ft.ScrollMode.HIDDEN),
            border_radius=14, expand=3, padding=5, bgcolor="#0D0D0D"
        )

        self.folder_list = ft.ListView(expand=True, spacing=5)

        self.folder_controls = ft.Row([
            ft.IconButton(icon=ft.Icons.CREATE_NEW_FOLDER_OUTLINED, icon_color="white70", icon_size=20),
            ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_color="white70", icon_size=20),
            ft.IconButton(icon=ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color="redaccent_200", icon_size=20),
        ], alignment=ft.MainAxisAlignment.START, spacing=0)

        self.content = ft.Row([
            ft.Column([
                ft.Container(content=self.folder_controls, padding=ft.Padding(left=5), margin=ft.Margin(top=10)),
                ft.Container(content=self.folder_list, border_radius=14, expand=True, padding=10, 
                             margin=ft.Margin.only(bottom=30), bgcolor="#0D0D0D"),
            ], expand=1, spacing=5),
            
            ft.Column([
                ft.Container(content=self.track_header_controls, padding=ft.Padding(left=10, right=10, top=10)),
                self.track_list_panel
            ], expand=3, spacing=10)
        ], spacing=10, expand=True, 
        vertical_alignment=ft.CrossAxisAlignment.STRETCH)
    
    def _process_and_sort_data(self, raw_data):
        """ПРОСТО ПОВЕРТАЄ ДАНІ ЯК Є. Сортування та групування вимкнено."""
        return raw_data if raw_data else []

    async def _apply_sort(self, criterion):
        """Тільки оновлює UI кнопки та записує вибір, без реальної перетасовки списку."""
        self.sort_criterion = criterion
        self.sort_text.value = self.sort_labels[criterion]
        set_sort_setting(criterion)
        self.update()

    def format_duration(self, seconds):
        if not seconds: return "--:--"
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:02d}"

    def format_views(self, views):
        if not views: return "0 views"
        if views >= 1000000: return f"{views / 1000000:.1f}M views"
        if views >= 1000: return f"{views / 1000:.1f}K views"
        return f"{views} views"

    # --- INITIALIZATION ---

    async def initial_sync(self):
        self._sync_folders_ui()
        data = self.backend.get_playlist_dicts()
        await self._render_tracks_progressive(data)

    # --- RENDERING LOGIC ---

    async def _render_tracks_progressive(self, tracks_data):
        async with self.render_lock:
            self.all_tracks_data = self._process_and_sort_data(tracks_data)
            self.track_list.controls.clear()
            
            if not self.all_tracks_data:
                self.track_list.controls.append(ft.Text("No tracks found", color="white30"))
                self.load_more_btn.visible = False
            else:
                chunk = self.all_tracks_data[:self.visible_count]
                new_controls = []
                last_album = None
                
                for i, t in enumerate(chunk):
                    current_album = t.get("album") or "General"
                    if current_album != last_album:
                        new_controls.append(self._create_section_header(current_album))
                        last_album = current_album
                    new_controls.append(self._create_track_item(t, i))
                
                self.track_list.controls = new_controls
                self._check_pagination_visibility()
            
            self.playlist_title.value = self.current_playlist_name.upper()
            self.update()

    async def _handle_load_more_click(self, e):
        if self._is_loading_now: return
        async with self.render_lock:
            self._is_loading_now = True
            self.load_more_btn.visible = False
            self.loader.visible = True
            self.update()
            await asyncio.sleep(0.1)
            await self._load_next_chunk()
            self.loader.visible = False
            self._check_pagination_visibility()
            self.update()
            self._is_loading_now = False

    def _check_pagination_visibility(self):
        current_visible = sum(1 for c in self.track_list.controls if isinstance(c, ft.ListTile))
        self.load_more_btn.visible = current_visible < len(self.all_tracks_data)

    async def _load_next_chunk(self):
        current_visible_tracks_count = sum(1 for c in self.track_list.controls if isinstance(c, ft.ListTile))
        if current_visible_tracks_count >= len(self.all_tracks_data): return

        next_chunk_end = current_visible_tracks_count + self.visible_count
        next_data = self.all_tracks_data[current_visible_tracks_count:next_chunk_end]
        
        last_playlist_context = None
        if current_visible_tracks_count > 0:
            last_track_data = self.all_tracks_data[current_visible_tracks_count - 1]
            last_playlist_context = last_track_data.get("album") or "General"

        new_items = []
        running_context = last_playlist_context

        for i, t in enumerate(next_data):
            track_playlist = t.get("album") or "General"
            if track_playlist != running_context:
                new_items.append(self._create_section_header(track_playlist))
                running_context = track_playlist 
            new_items.append(self._create_track_item(t, current_visible_tracks_count + i))
            
        self.track_list.controls.extend(new_items)
        self.track_list.update()

    def _create_section_header(self, playlist_name: str):
        return ft.Container(
            content=ft.Text(value=playlist_name.upper(), size=11, weight="bold", color="blueaccent", opacity=0.8, italic=True),
            padding=ft.Padding(left=15, top=20, bottom=5),
        )

    def _create_track_item(self, track_data, index):
        is_current = False
        if self.backend.current_track:
            is_current = track_data.get("path") == self.backend.current_track.path
        
        # БЕРЕМО ВЖЕ ГОТОВІ РЯДКИ З БЕКЕНДУ
        duration_text = track_data.get("duration_pretty", "--:--")
        views_text = track_data.get("views_pretty", "0 views")
        upload_date = track_data.get("upload_date") or "Unknown date"

        return ft.ListTile(
            data=index,
            leading=self._get_cover_ui(track_data.get("thumbnail_url")),
            title=ft.Text(
                track_data.get("title") or "Unknown", 
                size=13, weight="w500", max_lines=1, no_wrap=True, 
                color="blueaccent" if is_current else "white"
            ),
            subtitle=ft.Row([
                ft.Text(track_data.get("artist") or "Unknown", size=11, color="white60"),
                ft.Text("•", size=11, color="white30"),
                ft.Text(upload_date, size=10, color="white30"),
            ], spacing=5),
            trailing=ft.Column([
                ft.Text(duration_text, size=12, weight="bold", color="white70"),
                ft.Text(views_text, size=9, color="white30"),
            ], horizontal_alignment=ft.CrossAxisAlignment.END, alignment=ft.MainAxisAlignment.CENTER, spacing=0),
            bgcolor=ft.Colors.with_opacity(0.1, "blueaccent") if is_current else None,
            on_click=lambda _: self.page.run_task(self._handle_track_click, index),
        )

    def _get_cover_ui(self, ui_path):
        if ui_path:
            return ft.Image(src=ui_path, width=40, height=40, fit="cover", border_radius=6, gapless_playback=True)
        return ft.Container(width=40, height=40, bgcolor="white10", border_radius=6, alignment=ft.alignment.Alignment(0,0), content=ft.Text("♪", size=18, color="white30"))

    def _sync_folders_ui(self):
        self.folder_list.controls.clear()
        self.folder_list.controls.append(self._get_global_item())
        self.folder_list.controls.append(ft.Divider(height=1, color="white10"))
        
        for f in sorted(self.backend._by_playlist.keys()):
            playlist_tracks = self.backend._by_playlist[f]
            folder_cover = next((getattr(t, "artist_thumbnail", None) or getattr(t, "cover_path", None) for t in playlist_tracks if getattr(t, "artist_thumbnail", None) or getattr(t, "cover_path", None)), None)
            
            leading_element = ft.Container(
                content=ft.Image(src=folder_cover, width=32, height=32, fit="cover", gapless_playback=True) if folder_cover else ft.Icon(ft.Icons.FOLDER_OPEN_OUTLINED, size=18, color="white40"),
                width=32, height=32, border_radius=16, bgcolor="white10" if not folder_cover else None, clip_behavior=ft.ClipBehavior.HARD_EDGE
            )

            self.folder_list.controls.append(
                ft.ListTile(leading=leading_element, title=ft.Text(f, size=13, weight="w500", no_wrap=True), 
                            on_click=lambda e, name=f: self._safe_folder_select(name), visual_density=ft.VisualDensity.COMPACT)
            )
        self.folder_list.update()

    def _get_global_item(self):
        return ft.ListTile(
            leading=ft.Icon(ft.Icons.ALL_INBOX_ROUNDED, color="blueaccent", size=22),
            title=ft.Text("GLOBAL PLAYLIST", size=13, weight="bold", color="blueaccent"),
            on_click=lambda _: self.page.run_task(self._on_global_click),
            bgcolor=ft.Colors.with_opacity(0.05, "blueaccent"),
            shape=ft.RoundedRectangleBorder(radius=10), 
        )

    async def _handle_track_click(self, index: int):
        current_ui_paths = [t["path"] for t in self.all_tracks_data]
        if self._on_track_select_index:
            self._on_track_select_index(index, current_ui_paths)
        else:
            self.backend.play_track(index=index, playlist=current_ui_paths)
        self.update_highlight()

    async def _on_folder_select(self, folder_name):
        data = await asyncio.get_running_loop().run_in_executor(
            None, self.backend.set_playlist_from_folder, folder_name
        )
        if data or folder_name == self.current_playlist_name:
            self.current_playlist_name = folder_name
            await self._render_tracks_progressive(data)

    async def _on_global_click(self, e=None):
        self.current_playlist_name = "GLOBAL PLAYLIST"
        data = await asyncio.get_running_loop().run_in_executor(None, self.backend.set_global_playlist)
        await self._render_tracks_progressive(data)

    def _safe_folder_select(self, name):
        if self.page: 
            self.page.run_task(self._on_folder_select, name)
        
    def update_highlight(self):
        if not self.page or not self.track_list.controls or not self.backend.current_track: return
        current_path = self.backend.current_track.path
        has_changes = False
        for control in self.track_list.controls:
            if isinstance(control, ft.ListTile):
                try:
                    track_idx = control.data
                    is_current = self.all_tracks_data[track_idx]["path"] == current_path
                    new_bg = ft.Colors.with_opacity(0.1, "blueaccent") if is_current else None
                    if control.bgcolor != new_bg:
                        control.bgcolor = new_bg
                        control.title.color = "blueaccent" if is_current else "white"
                        has_changes = True
                except: continue
        if has_changes: self.track_list.update()

    def did_mount(self):
        self.backend.add_track_change_listener(lambda _: self.page.run_task(self.update_ui_async) if self.page else None)
        self.page.pubsub.subscribe_topic("player_scroll", lambda t, p: self.page.run_task(self.scroll_to_track_by_path, p))
        self.page.run_task(self.initial_sync)

    async def update_ui_async(self):
        self.update_highlight()

    async def scroll_to_track_by_path(self, path):
        target_index = next((i for i, t in enumerate(self.all_tracks_data) if t.get("path") == path), None)
        if target_index is None: return
        current_count = sum(1 for c in self.track_list.controls if isinstance(c, ft.ListTile))
        if target_index >= current_count:
            self.visible_count = target_index + 5
            await self._load_next_chunk()
        self.track_list.scroll_to(key=str(target_index), duration=1000, curve=ft.AnimationCurve.DECELERATE)