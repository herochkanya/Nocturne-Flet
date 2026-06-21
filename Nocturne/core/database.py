# Core database module for the Music Player
import os, json, sys, sqlite3, shutil, hashlib, requests

# --- Path helpers ---
def get_project_root():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = os.path.dirname(get_project_root()) if get_project_root().endswith('core') else get_project_root()
DATABASE_DIR = os.path.join(PROJECT_ROOT, "database")
SETTINGS_FILE = os.path.join(DATABASE_DIR, "settings.json")
LIBRARY_DB_FILE = os.path.join(DATABASE_DIR, "library.db")
COVERS_DIR = os.path.join(DATABASE_DIR, "covers")

os.makedirs(DATABASE_DIR, exist_ok=True)
os.makedirs(COVERS_DIR, exist_ok=True)

# --- SQLite Initialization ---
def init_db():
    conn = sqlite3.connect(LIBRARY_DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        artist TEXT,
        album TEXT,
        path TEXT,
        lyrics_path TEXT,
        thumbnail_url TEXT,
        artist_thumbnail TEXT,
        source_url TEXT,
        upload_date TEXT,
        view_count INTEGER,
        duration INTEGER,
        tags TEXT,
        categories TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

# --- Cover Management ---

def ensure_cover_cached(key: str, url: str, fallback_url: str = None) -> str | None:
    """
    Завантажує та кешує зображення. 
    Якщо всі спроби для основного URL (наприклад, аватар артиста) провалені,
    спробує завантажити fallback_url (обкладинку відео).
    """
    if not url or not url.startswith("http"):
        return url

    if not os.path.exists(COVERS_DIR):
        os.makedirs(COVERS_DIR, exist_ok=True)

    file_hash = hashlib.md5(key.encode()).hexdigest()
    local_path = os.path.join(COVERS_DIR, f"{file_hash}.jpg")

    if os.path.exists(local_path):
        return local_path

    # Список стратегій завантаження
    urls_to_try = []
    
    # 1. Модифікований Google URL
    target_url = url
    if "ggpht.com" in url or "googleusercontent.com" in url:
        target_url = url.replace("/ytc/", "/a/")
        if "=" in target_url:
            target_url = target_url.split('=')[0] + "=s256-c-k-c0x00ffffff-no-rj"
    urls_to_try.append(target_url)

    # 2. План Б: Оригінал
    if url not in urls_to_try:
        urls_to_try.append(url)

    # 3. План В: Резервне фото (якщо передано)
    if fallback_url and fallback_url.startswith("http"):
        urls_to_try.append(fallback_url)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
    }

    print(f"🖼️ Nocturne Cache: завантаження {key[:20]}...")

    for attempt_url in urls_to_try:
        try:
            # Спроба завантаження
            response = requests.get(attempt_url, headers=headers, timeout=5, verify=False)
            
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Успішно: {attempt_url[:30]}...")
                return local_path
            
            print(f"⚠️ Спроба невдала ({response.status_code}): {attempt_url[:30]}...")
        except Exception:
            continue

    print(f"❌ Всі спроби для {key[:20]} провалені.")
    return None

def add_track_to_db(track_data: dict):
    conn = sqlite3.connect(LIBRARY_DB_FILE)
    c = conn.cursor()
    # Використовуємо REPLACE, щоб оновлювати існуючі треки
    c.execute('''INSERT OR REPLACE INTO tracks 
        (title, artist, album, path, lyrics_path, thumbnail_url, source_url, 
         artist_thumbnail, upload_date, view_count, duration, tags, categories)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
        track_data.get('title'), track_data.get('artist'), track_data.get('album'), 
        track_data.get('path'), track_data.get('lyrics_path'), track_data.get('thumbnail_url'),
        track_data.get('source_url'), track_data.get('artist_thumbnail'),
        track_data.get('upload_date'), track_data.get('view_count'),
        track_data.get('duration'), 
        json.dumps(track_data.get('tags', [])), 
        json.dumps(track_data.get('categories', []))
    ))
    conn.commit()
    conn.close()

def load_library_cache() -> list:
    conn = sqlite3.connect(LIBRARY_DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tracks")
    rows = c.fetchall()
    
    library = []
    for row in rows:
        track = dict(row)
        track['tags'] = json.loads(track['tags'])
        track['categories'] = json.loads(track['categories'])
        library.append(track)
    conn.close()
    return library

# --- Settings Management ---

def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠️ settings.json was hurt — creating a new one.")
    return {}

def save_settings(data: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_theme() -> str: return load_settings().get("theme", "green")
def set_theme(theme_name: str):
    settings = load_settings()
    settings["theme"] = theme_name
    save_settings(settings)

def get_download_path_setting() -> str | None: return load_settings().get("download_path")
def set_download_path_setting(path: str):
    settings = load_settings()
    settings["download_path"] = path
    save_settings(settings)

def get_language() -> str: return load_settings().get("language", "en")
def set_language(lang: str):
    settings = load_settings()
    settings["language"] = lang
    save_settings(settings)

def get_custom_background() -> str | None: return load_settings().get("custom_background")
def set_custom_background(path: str):
    settings = load_settings()
    settings["custom_background"] = path
    save_settings(settings)

def get_animation_settings() -> dict:
    return load_settings().get("animation_settings", {"screen": True, "cover": True, "pulse": True})
def set_animation_settings(animation_settings: dict):
    settings = load_settings()
    settings["animation_settings"] = animation_settings
    save_settings(settings)

def get_cover_settings() -> dict: return load_settings().get("cover_settings", {"style": "circle"})
def set_cover_settings(cover_settings: dict):
    settings = load_settings()
    settings["cover_settings"] = cover_settings
    save_settings(settings)

def get_equalizer_settings() -> dict:
    return load_settings().get("equalizer", {"60": 0, "150": 0, "400": 0, "1000": 0, "2400": 0, "15000": 0})
def set_equalizer_settings(eq_settings: dict):
    settings = load_settings()
    settings["equalizer"] = eq_settings
    save_settings(settings)

def get_shortcuts() -> dict:
    return load_settings().get("shortcuts", {"play_pause": ["ctrl", "space"], "next": ["ctrl", "right"], "prev": ["ctrl", "left"]})
def set_shortcuts(shortcuts: dict):
    settings = load_settings()
    settings["shortcuts"] = shortcuts
    save_settings(settings)

def get_lite_mode() -> bool: return load_settings().get("lite_mode", False)
def set_lite_mode(state: bool):
    settings = load_settings()
    settings["lite_mode"] = state
    save_settings(settings)

def get_tray_mode() -> bool: return load_settings().get("tray_mode", False)
def set_tray_mode(state: bool):
    settings = load_settings()
    settings["tray_mode"] = state
    save_settings(settings)

def get_ui_layout() -> str | None: return load_settings().get("ui_layout")
def set_ui_layout(layout_name: str):
    settings = load_settings()
    settings["ui_layout"] = layout_name
    save_settings(settings)

# --- Sorting & Hierarchy Settings ---

def get_sort_setting() -> str: 
    return load_settings().get("sort_criterion", "alphabet")

def set_sort_setting(criterion: str):
    settings = load_settings()
    settings["sort_criterion"] = criterion
    save_settings(settings)

def get_hierarchy_setting() -> bool:
    """Get the 'Keep Folder Structure' toggle state."""
    return load_settings().get("keep_hierarchy", True)

def set_hierarchy_setting(state: bool):
    """Set the 'Keep Folder Structure' toggle state."""
    settings = load_settings()
    settings["keep_hierarchy"] = state
    save_settings(settings)
