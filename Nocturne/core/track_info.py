### track_info.py

# Core module to read track metadata using mutagen
# There is only TrackInfo class here

import os
import hashlib
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from typing import Optional, Dict
from core.database import COVERS_DIR

class TrackInfo:
    def __init__(self, path: str, load_metadata: bool = True, cached_data: Optional[Dict] = None):
        self.path = path
        # Ініціалізуємо всі поля значеннями за замовчуванням
        self.title = os.path.basename(path)
        self.artist = 'Unknown Artist'
        self.album = 'Unknown Album'
        self.cover_path = None
        self.lyrics_path = None
        self.source_url = None
        self.artist_thumbnail = None
        self.duration = 0
        self.upload_date = None
        self.view_count = 0
        self.tags = []
        
        if cached_data:
            self.title = cached_data.get('title', self.title)
            self.artist = cached_data.get('artist', self.artist)
            self.album = cached_data.get('album', self.album)
            self.cover_path = cached_data.get('thumbnail_url')
            self.lyrics_path = cached_data.get('lyrics_path')
            self.source_url = cached_data.get('source_url')
            self.artist_thumbnail = cached_data.get('artist_thumbnail')
            self.duration = cached_data.get('duration', 0)
            raw_date = cached_data.get('upload_date')
            self.upload_date = self._format_raw_date(raw_date)
            self.view_count = cached_data.get('view_count', 0)
            self.tags = cached_data.get('tags', [])
        else:
            self.title = os.path.basename(path)
            self.artist = 'Unknown Artist'
            self.album = 'Unknown Album'
            self.cover_path = None
            if load_metadata:
                self._read_metadata()
    
    @property
    def duration_pretty(self) -> str:
        if not self.duration: return "--:--"
        return f"{int(self.duration // 60)}:{int(self.duration % 60):02d}"

    @property
    def views_pretty(self) -> str:
        v = self.view_count or 0
        if v >= 1_000_000: return f"{v / 1_000_000:.1f}M views"
        if v >= 1_000: return f"{v / 1_000:.1f}K views"
        return f"{v} views"

    @staticmethod
    def format_time(seconds: float) -> str:
        if not seconds or seconds < 0: return "0:00"
        m, s = divmod(int(seconds), 60)
        return f"{m}:{s:02d}"
    
    def _format_raw_date(self, date_str):
        """Перетворює 20240404 на 2024-04-04"""
        if not date_str or not isinstance(date_str, str):
            return date_str
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        return date_str

    def _read_metadata(self):
        try:
            audio = MP3(self.path, ID3=ID3)
            tags = audio.tags or {}
        except Exception:
            tags = {}

        self.title = tags.get('TIT2').text[0] if tags.get('TIT2') else os.path.basename(self.path)
        self.artist = tags.get('TPE1').text[0] if tags.get('TPE1') else 'Unknown Artist'
        self.album = tags.get('TALB').text[0] if tags.get('TALB') else 'Unknown Album'

        # Екстракція обкладинки
        try:
            for frame in tags.values():
                if isinstance(frame, APIC):
                    image_data = frame.data
                    if not image_data: continue

                    img_hash = hashlib.md5(image_data).hexdigest()
                    ext = '.png' if 'png' in getattr(frame, 'mime', '').lower() else '.jpg'
                    cache_path = os.path.join(COVERS_DIR, f"{img_hash}{ext}")

                    if not os.path.exists(cache_path):
                        with open(cache_path, 'wb') as f:
                            f.write(image_data)
                    
                    self.cover_path = cache_path
                    break 
        except Exception:
            self.cover_path = None

    def as_dict(self) -> Dict:
        # Перевірка: чи не "протух" шлях до обкладинки
        actual_cover = self.cover_path
        if actual_cover and not actual_cover.startswith("http") and not os.path.exists(actual_cover):
            self.cover_path = None

        return {
            'path': self.path,
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'thumbnail_url': self.cover_path,
            'lyrics_path': self.lyrics_path,
            'source_url': self.source_url,
            'artist_thumbnail': self.artist_thumbnail,
            'duration': self.duration,
            'upload_date': self.upload_date,
            'view_count': self.view_count,
            'tags': self.tags,
            "duration_pretty": self.duration_pretty,
            "views_pretty": self.views_pretty,
        }

    def cleanup_orphan_covers(self):
        """Видаляє файли обкладинок, які не прив'язані до жодного треку в бібліотеці."""
        if not self._library_ready:
            return

        # 1. Збираємо ВСІ активні картинки з обох полів
        active_covers = set()
        for track in self._library:
            # Перевіряємо обкладинку треку
            if track.cover_path and not track.cover_path.startswith("http"):
                active_covers.add(os.path.basename(track.cover_path))
            
            # Перевіряємо фото артиста (Artist Thumbnail) — ТУТ БУЛА ДІРКА
            if hasattr(track, 'artist_thumbnail') and track.artist_thumbnail:
                if not track.artist_thumbnail.startswith("http"):
                    active_covers.add(os.path.basename(track.artist_thumbnail))

        # 2. Скануємо фізичну папку з обкладинками
        try:
            from core.database import COVERS_DIR
            if not os.path.exists(COVERS_DIR):
                return
                
            all_stored_covers = os.listdir(COVERS_DIR)
            deleted_count = 0
            
            for cover_file in all_stored_covers:
                # 3. Видаляємо файл тільки якщо його немає НІ В ОДНОМУ з полів
                if cover_file not in active_covers:
                    file_path = os.path.join(COVERS_DIR, cover_file)
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        print(f"❌ Помилка видалення {cover_file}: {e}")
            
            if deleted_count > 0:
                print(f"🧹 Прибирання завершено: видалено {deleted_count} сирітських файлів.")
        except Exception as e:
            print(f"⚠️ Не вдалося провести очищення: {e}")
