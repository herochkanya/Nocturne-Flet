import flet as ft
import asyncio, functools, os, re
from core.downloader import download_audio
from core.database import add_track_to_db
from config import AppColors

class DownloaderScreen(ft.Container):
    def __init__(self, backend):
        super().__init__(visible=False, expand=True, padding=20, border_radius=10)
        self.backend = backend
        self.margin = ft.Margin.symmetric(horizontal=10) 
        self.bgcolor = AppColors.BG_MAIN
        self.queue_items = {}

        # --- SHARED STYLES ---
        self.container_style = {
            "bgcolor": AppColors.BG_CARD, 
            "border_radius": 10, 
            "padding": 10, 
            "border": None
        }

        # --- UI COMPONENTS ---
        self.url_list = ft.ListView(expand=True, spacing=10)
        self.existing_folders_list = ft.ListView(expand=True, spacing=5)
        
        self.folder_input = ft.TextField(
            hint_text="Enter folder name", 
            hint_style=ft.TextStyle(color=AppColors.TEXT_MUTED),
            height=40, border_radius=10, bgcolor=AppColors.BG_PLAYER_BAR,
            color=AppColors.TEXT_PRIMARY, text_size=12,
            prefix=ft.Container(
                content=ft.Icon(ft.Icons.FOLDER_OPEN_ROUNDED, color=AppColors.TEXT_MUTED, size=20),
                padding=ft.padding.only(left=10, right=10),
                width=40, # Strictly locks the space so it never flickers or moves on click
            )
        )

        self.current_job_title = ft.Text("Waiting for task...", size=14, weight="w600", max_lines=1)
        self.progress_bar = ft.ProgressBar(value=0, color=AppColors.ACCENT, bgcolor=AppColors.PROGRESS_BAR, height=4)
        self.status_metrics = ft.Text("0% / 0 KB/s", size=11, color=AppColors.TEXT_MUTED)
        self.done_counter = ft.Text("Done: 0", size=11, weight="bold", color=AppColors.TEXT_PRIMARY)
        self.queue_list_view = ft.ListView(expand=True, spacing=5)

        # --- LAYOUT ---
        def section_title(text):
            return ft.Text(text.upper(), size=11, weight="bold", color=AppColors.TEXT_MUTED, style=ft.TextStyle(letter_spacing=1.5))

        self.content = ft.Row([
            ft.Column([
                section_title("Input Queue"),
                ft.Container(
                    content=ft.Stack([
                        ft.ListView([self.url_list, ft.Container(height=50)]),
                        ft.Container(
                            content=ft.TextButton(
                                "Add another link", 
                                icon=ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED, 
                                on_click=self._add_url_field,
                                width=200, height=40, style=ft.ButtonStyle(color=AppColors.ACCENT, text_style=ft.TextStyle(size=16))
                            ),
                            bottom=0, bgcolor=AppColors.BG_CARD
                        ),
                    ], alignment=ft.Alignment.TOP_CENTER), 
                    expand=True, **self.container_style
                ),
            ], spacing=15, expand=5),

            ft.Column([
                section_title("Destination"),
                self.folder_input,
                ft.Container(content=self.existing_folders_list, expand=True, **self.container_style),
                ft.FilledButton("DOWNLOAD", height=50, width=float("inf"), on_click=self._on_start_click, 
                                bgcolor=AppColors.ACCENT, style=ft.ButtonStyle(text_style=ft.TextStyle(size=18, weight="bold"))),
            ], spacing=15, expand=5),

            ft.Column([
                section_title("Active Session"), 
                self._get_status_card(),
                ft.Container(
                    content=ft.Row([ft.Text("QUEUE LIST", size=10, color=AppColors.TEXT_MUTED), self.done_counter], alignment="spaceBetween"),
                    padding=ft.Padding.symmetric(horizontal=5)
                ),
                ft.Container(content=self.queue_list_view, expand=True, **self.container_style),
            ], expand=6, spacing=15)
        ], spacing=30, expand=True)

    # --- UI HELPERS ---

    def _get_status_card(self):
        return ft.Container(
            bgcolor=AppColors.BG_CARD_2, border_radius=10, padding=15,
            content=ft.Column([
                ft.Row([ft.Icon(ft.Icons.CLOUD_DOWNLOAD_ROUNDED, color=AppColors.ACCENT, size=20),
                        ft.Text("ENGINE STATUS", size=10, weight="bold", color=AppColors.ACCENT)], spacing=10),
                self.current_job_title,
                self.progress_bar,
                self.status_metrics
            ], spacing=10)
        )

    # --- PROGRESS & DOWNLOAD LOGIC ---

    def _update_progress_ui(self, d):
        if d['status'] == 'downloading':
            try:
                p_raw = d.get('_percent_str', '0%')
                p_clean = re.sub(r'\x1b\[[0-9;]*m', '', p_raw).replace('%', '').strip()
                p_float = float(p_clean) / 100.0
                filename = os.path.basename(d.get('filename', 'Unknown'))
                if len(filename) > 40: filename = filename[:37] + "..."
                speed = re.sub(r'\x1b\[[0-9;]*m', '', d.get('_speed_str', 'N/A')).strip()
                total = d.get('_total_bytes_str', d.get('_total_bytes_estimate_str', 'N/A'))
                
                self.current_job_title.value = f"Downloading: {filename}"
                self.progress_bar.value = p_float
                self.status_metrics.value = f"{p_clean}% | {speed} | Total: {total}"
                if self.page: self.page.update()
            except Exception as e: print(f"UI Update Error: {e}") 

        elif d['status'] == 'finished':
            self.current_job_title.value = "Finalizing (Applying Tags)..."
            self.progress_bar.value = None
            if self.page: self.page.update()

    async def _on_start_click(self, e):
        raw_links = [row.controls[0].value.strip() for row in self.url_list.controls 
                     if isinstance(row, ft.Row) and row.controls[0].value.strip()]
        
        if not raw_links:
            self.current_job_title.value = "⚠️ No links provided"
            self.update()
            return

        links = list(dict.fromkeys(raw_links))
        folder = self.folder_input.value.strip() or "downloads"
        loop = asyncio.get_running_loop()
        
        self.queue_list_view.controls.clear()
        self.queue_items = {}
        self.done_counter.value = "Done: 0"
        self.update()

        for url in links:
            if not url.startswith(("http://", "https://")): continue

            def on_metadata(title):
                item = ft.ListTile(
                    title=ft.Text(f"⏳ {title}", size=12),
                    subtitle=ft.Text("Pending...", size=10, color=AppColors.TEXT_MUTED),
                    leading=ft.ProgressRing(width=16, height=16, stroke_width=2),
                    dense=True
                )
                self.queue_list_view.controls.insert(0, item)
                self.queue_items[title] = item
                if self.page: self.page.update()

            self.current_job_title.value = f"🔍 Analyzing: {url[:30]}..."
            self.progress_bar.value = None
            self.update()

            func = functools.partial(download_audio, url=url, target_folder=folder, 
                                     progress_cb=self._update_progress_ui, metadata_cb=on_metadata)

            try:
                res = await loop.run_in_executor(None, func)
                if res:
                    tracks = res if isinstance(res, list) else [res]
                    for track in tracks:
                        if not isinstance(track, dict):
                            print(f"DEBUG: Skipping invalid track format: {type(track)}")
                            continue
                            
                        if track.get('artist_thumbnail') is None:
                            track['artist_thumbnail'] = track.get('channel_url') or ""
                        
                        try:
                            add_track_to_db(track)
                            print(f"✅ Saved to DB: {track.get('title')}")
                        except Exception as db_err:
                            print(f"❌ DB Save Error: {db_err}")
                        t_name = track.get('title')
                        ui_item = next((item for key, item in self.queue_items.items() if t_name in key or key in t_name), None)
                        if ui_item:
                            ui_item.title.value = f"✅ {t_name}"
                            ui_item.subtitle.value = f"Finished | Saved to /{folder}"
                            ui_item.leading = ft.Icon(ft.Icons.CHECK_CIRCLE, color="green", size=18)
                    self.current_job_title.value = "✅ Task completed"
                    self.progress_bar.value = 1.0
                else:
                    self.current_job_title.value = "❌ Engine error"
                    self.progress_bar.value = 0
                    for item in self.queue_items.values():
                        if "⏳" in item.title.value:
                            item.title.value = item.title.value.replace("⏳", "❌")
                            item.leading = ft.Icon(ft.Icons.ERROR, color="red", size=18)
            except Exception as ex:
                self.current_job_title.value = f"❌ Fatal: {str(ex)[:40]}"
            
            done_count = sum(1 for item in self.queue_list_view.controls if isinstance(item, ft.ListTile) and "✅" in item.title.value)
            self.done_counter.value = f"Done: {done_count}"
            if self.page: self.page.update()
            await asyncio.sleep(1)
        
        self.backend.build_library_index()

        if any("✅" in str(c.title.value) for c in self.queue_list_view.controls):
             self.current_job_title.value = "🏁 All session tasks finished"
             self.status_metrics.value = "Standing by..."
             self.progress_bar.value = 0
             self.update()

    # --- INITIALIZATION & UTILS ---

    def _add_url_field(self, e=None):
        url_input = ft.TextField(hint_text="Paste your YouTube link here", 
                                 hint_style=ft.TextStyle(color=AppColors.TEXT_MUTED),
                                 height=40, border_radius=10, color=AppColors.TEXT_PRIMARY,
                                 text_size=12, bgcolor=AppColors.BG_PLAYER_BAR, expand=True)
        field_container = ft.Row(spacing=5, controls=[url_input, ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=AppColors.TEXT_MUTED, icon_size=18,
            on_click=lambda e: (self.url_list.controls.remove(field_container) if len(self.url_list.controls) > 1 else setattr(url_input, 'value', ""), self.update()))
        ])
        self.url_list.controls.append(field_container)
        self.update()

    def _select_folder(self, folder_name):
        self.folder_input.value = folder_name
        self.update()

    async def initial_sync(self):
        self.existing_folders_list.controls.clear()
        folders = sorted(self.backend._by_playlist.keys()) if hasattr(self.backend, '_by_playlist') else []
        for folder in folders:
            self.existing_folders_list.controls.append(ft.ListTile(
                title=ft.Text(folder, size=12, color=AppColors.TEXT_PRIMARY),
                leading=ft.Icon(ft.Icons.FOLDER_OPEN_OUTLINED, size=16, color=AppColors.TEXT_MUTED),
                dense=True, on_click=lambda e, f=folder: self._select_folder(f)
            ))
        if not self.url_list.controls: self._add_url_field()
        self.update()
