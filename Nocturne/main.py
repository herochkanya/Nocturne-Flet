import flet as ft
import asyncio
import os, inspect
from core.database import DATABASE_DIR, get_ui_layout, set_ui_layout
from core.player import MusicPlayer

# UI
from interface.header_ui import AppHeader
from interface.player_bar_ui import AppPlayerBar
from interface.playlist_ui import PlaylistNavigation
from interface.track_info_ui import TrackDetails
from interface.player_classic_ui import PlayerScreen
from interface.player_modern_ui import PlayerModernScreen
from interface.downloader_ui import DownloaderScreen
from interface.settings_ui import SettingsScreen

async def main(page: ft.Page):
    # --- CONFIG ---
    page.title = "Nocturne"
    page.bgcolor = ft.Colors.BLACK
    page.padding = 0
    page.spacing = 0

    # Налаштування вікна (через page.window для стабільності)
    page.window.width = 1020
    page.window.height = 720
    page.window.min_width = 820
    page.window.min_height = 620
    page.window.title_bar_hidden = True
    page.window.title_bar_buttons_visible = False
    page.window.prevent_close = True
    page.window.update() # Застосовуємо налаштування відразу

    backend = MusicPlayer()
    chosen_layout = get_ui_layout()
    
    # Отримуємо loop один раз для всього додатка
    loop = asyncio.get_running_loop()

    # --- START APP ---
    async def start_app(layout_style: str):
        set_ui_layout(layout_style)
        page.controls.clear()

        loader = ft.Column(
            [
                ft.ProgressRing(width=50, height=50, stroke_width=2),
                ft.Container(height=20),
                ft.Text(f"Loading {layout_style.capitalize()} Interface..."),
            ],
            alignment="center",
            horizontal_alignment="center",
            expand=True,
        )

        page.add(loader)
        page.update()

        # Тепер loop доступний тут
        await loop.run_in_executor(None, backend.build_library_index)
        backend.set_global_playlist()

        page.controls.clear()
        await build_main_ui(layout_style)

    # --- LAYOUT SELECTION ---
    async def select_layout_ui():
        header = AppHeader(page, None, None, None)
        
        def on_hover(e):
            e.control.border = ft.border.all(2, ft.Colors.BLUE_ACCENT) if e.data == "true" else ft.Border.all(1, ft.Colors.WHITE24)
            e.control.scale = 1.05 if e.data == "true" else 1.0
            e.control.bgcolor = "#2c2f33" if e.data == "true" else "#1e2124"
            e.control.update()

        def create_card(title, desc, icon_str, layout_key):
            return ft.GestureDetector(
                mouse_cursor="click",
                on_tap=lambda _: page.run_task(start_app, layout_key),
                content=ft.Container(
                    content=ft.Column([
                        ft.Icon(icon_str, size=50, color=ft.Colors.BLUE_ACCENT),
                        ft.Text(title, size=24, weight="bold"),
                        ft.Text(desc, text_align="center", color="white70"),
                    ], alignment="center", horizontal_alignment="center", spacing=10),
                    width=300, height=400, padding=30,
                    border=ft.Border.all(1, ft.Colors.WHITE24),
                    border_radius=20, bgcolor="#1e2124",
                    on_hover=on_hover,
                    animate_scale=ft.Animation(300, "decelerate"),
                )
            )

        # Додаємо хедер ПЕРШИМ, щоб він був зверху
        page.add(
            header,
            ft.Container(
                content=ft.Column([
                    ft.Text("Welcome to Nocturne", size=40, weight="bold"),
                    ft.Text("Choose your preferred interface style", color="white70"),
                    ft.Row([
                        create_card("Classic", "Traditional list player", ft.Icons.LIST, "classic"),
                        create_card("Modern", "Immersive widgets", ft.Icons.DASHBOARD, "modern"),
                    ], alignment="center", spacing=30),
                ], alignment="center", horizontal_alignment="center", spacing=40),
                expand=True
            )
        )
        page.update()

    # --- MAIN UI ---
    async def build_main_ui(layout_style: str):
        history, future = ["player"], []
        
        p_nav = PlaylistNavigation()
        t_info = TrackDetails()

        MIN_WIDE_WIDTH = 1050

        def manage_panels(opened_panel):
            if page.width < MIN_WIDE_WIDTH: # If it's tight
                if opened_panel == "right" and p_nav.is_expanded:
                    p_nav.toggle_state(force_close=True)
                elif opened_panel == "left" and t_info.is_expanded:
                    t_info.toggle_state(force_close=True)

        # 2. Inject the logic into instances
        p_nav.on_toggle = lambda: manage_panels("left")
        t_info.on_toggle = lambda: manage_panels("right")

        # --- CLEAN ARCHITECTURE RESIZE ---
        async def handle_resize(e):
            # 1. Отримуємо актуальну ширину прямо з об'єкта сторінки
            current_width = page.window.width if page.window.width else page.width
            
            # Дебаг: розкоментуй, щоб побачити чи летять івенти в термінал
            # print(f"Resize event: {current_width}px | Left: {p_nav.is_expanded} | Right: {t_info.is_expanded}")

            if current_width < MIN_WIDE_WIDTH:
                if p_nav.is_expanded and t_info.is_expanded:
                    # Викликаємо закриття лівої панелі
                    p_nav.toggle_state(force_close=True)
                    # Після зміни стану обов'язково оновлюємо сторінку
                    page.update() 

        # Спробуй призначити на обидва івенти для надійності
        page.on_resize = handle_resize

        p_bar = AppPlayerBar(backend, layout_style)

        is_modern = (layout_style == "modern")
        p_nav.visible = is_modern
        t_info.visible = is_modern

        # --- ЗМІНЕНО: БЕЗПЕЧНЕ ПЕРЕМИКАННЯ ЕКРАНІВ ---
        async def change_screen(name, save_history=True):
            if save_history and (not history or history[-1] != name):
                history.append(name)
                future.clear()
            
            # Допоміжна функція для виклику методу, тільки якщо він існує
            async def call_if_exists(obj, method_name):
                if hasattr(obj, method_name):
                    method = getattr(obj, method_name)
                    if inspect.iscoroutinefunction(method):
                        await method()
                    else:
                        method()

            # Логіка ініціалізації/очищення
            if name == "player":
                await call_if_exists(p_screen, "initial_sync")
            elif name == "downloader":
                await call_if_exists(d_screen, "initial_sync")
                await call_if_exists(p_screen, "cleanup")
            else:
                await call_if_exists(p_screen, "cleanup")
            
            # Перемикання видимості (залишається як було)
            p_screen.visible = (name == "player")
            d_screen.visible = (name == "downloader")
            s_screen.visible = (name == "settings")
            
            # Оновлення кнопок навігації
            header.back_btn.disabled = len(history) <= 1
            header.forward_btn.disabled = len(future) == 0
            
            # Оновлюємо UI
            header.update()
            central_content.update()

        page.change_screen = change_screen
        page.change_screen = change_screen

        p_screen = PlayerModernScreen(backend) if layout_style == "modern" else PlayerScreen(backend, on_change_screen=change_screen)
        d_screen = DownloaderScreen(backend=backend)

        async def refresh_all():
            await p_screen.initial_sync()

        d_screen.on_download_complete = refresh_all

        s_screen = SettingsScreen()

        central_content = ft.Stack([p_screen, d_screen, s_screen], expand=True)

        async def go_back():
            if len(history) > 1:
                future.append(history.pop())
                await change_screen(history[-1], False)

        async def go_forward():
            if future:
                history.append(future.pop())
                await change_screen(history[-1], False)

        header = AppHeader(
            page,
            on_screen_change=change_screen,
            on_back=go_back,
            on_forward=go_forward,
        )

        # Виправлено: тепер використовується глобальний loop
        async def handle_track_selection(index, playlist):
            await loop.run_in_executor(None, lambda: backend.play_track(index=index, playlist=playlist))

        if layout_style == "classic":
            p_screen._on_track_select_index = lambda i, p: page.run_task(handle_track_selection, i, p)

        backend.add_track_change_listener(lambda d: page.run_task(p_bar.update_track, d))
        backend.set_state_callback(lambda s: p_bar.update_state_ui(s))

        body_row = ft.Row(
            [p_nav, central_content, t_info], 
            spacing=0, 
            expand=True
        )

        page.add(
            header, 
            ft.Container(content=body_row, expand=True), 
            p_bar
        )
        page.update()
        page.run_task(track_progress, p_bar)

    async def track_progress(p_bar):
        while True:
            if backend.is_playing:
                try:
                    if p_bar.page:
                        info = backend.get_playback_info()
                        curr_pos = info.get("position", 0)
                        total_dur = info.get("duration", 0)

                        # Якщо слайдер ще не знає реальної тривалості (стоїть дефолтний 1.0)
                        # або якщо дані в бекенді змінилися, оновлюємо шкалу
                        if p_bar.slider.max != total_dur and total_dur > 0:
                            p_bar.slider.max = total_dur
                            p_bar.time_total.value = p_bar._format_time(total_dur)
                            p_bar.time_total.update()

                        # Тепер спокійно оновлюємо прогрес
                        p_bar.update_progress(curr_pos)
                        
                except Exception as e:
                    print(f"Progress sync error: {e}")
            await asyncio.sleep(0.8)

    # --- START LOGIC ---
    page.on_window_event = lambda e: (backend.stop_engine(), os._exit(0)) if e.data == "close" else None

    if chosen_layout:
        await start_app(chosen_layout)
    else:
        await select_layout_ui()

if __name__ == "__main__":
    ft.run(main, assets_dir=DATABASE_DIR)