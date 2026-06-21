# core/playlist.py

import os
import hashlib
from typing import List, Dict
from core.track_info import TrackInfo
from core.modes import Modes
from core.database import load_library_cache, add_track_to_db, ensure_cover_cached

class PlaylistManager(Modes, TrackInfo):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_playlists_for_set = set()
    
    def toggle_playlist_selection(self, folder: str):
        """Централізована логіка вибору папок."""
        if folder in self.selected_playlists_for_set:
            self.selected_playlists_for_set.remove(folder)
        else:
            self.selected_playlists_for_set.add(folder)
        
        # Викликаємо оновлення UI (якщо є такий метод у Modes)
        if hasattr(self, "update_playlist_highlight"):
            is_selected = folder in self.selected_playlists_for_set
            self.update_playlist_highlight(folder, is_selected)

    def set_playlist_from_folder(self, folder: str) -> List[Dict]:
        self.current_folder = folder
        
        # Якщо увімкнено режим вибору (multi-select)
        if getattr(self, "set_playlist_mode", False):
            self.toggle_playlist_selection(folder)
            return []

        self.current_query = {"type": "playlist", "value": folder}
        return self._apply_query()

    # ------------------ BUILD INDEX ------------------

    def build_library_index(self):
        """Smart scan using SQLite with resource auto-caching."""
        raw_cache = load_library_cache()
        cached_map = {item['path']: item for item in raw_cache}
        
        new_library = []
        self._by_playlist.clear()

        for root, _, files in os.walk(self.base_dir):
            folder_name = self._get_folder_name(root)
            if folder_name:
                self._by_playlist.setdefault(folder_name, [])

            for f in [f for f in files if f.lower().endswith(".mp3")]:
                path = os.path.normpath(os.path.join(root, f))
                
                if path in cached_map:
                    track = TrackInfo(path, load_metadata=False, cached_data=cached_map[path])
                    self._ensure_track_resources(track, cached_map[path], update_db=True)
                else:
                    track = TrackInfo(path, load_metadata=True)
                    self._ensure_track_resources(track)
                    add_track_to_db(track.as_dict())

                track.playlist = folder_name
                new_library.append(track)

        self._library = new_library
        self._library_ready = True
        
        # Build playlist index
        for t in self._library:
            if t.playlist:
                self._by_playlist.setdefault(t.playlist, []).append(t)
        
        self.cleanup_orphan_covers()

    def _get_folder_name(self, root_path: str) -> str:
        rel = os.path.relpath(root_path, self.base_dir)
        return None if rel == "." else rel.split(os.sep)[0]

    def _ensure_track_resources(self, track: TrackInfo, data: dict = None, update_db=False):
        """Validates and caches cover and artist images."""
        data = data or track.as_dict()
        
        # 1. Track Cover
        cover = data.get('thumbnail_url') or track.cover_path
        if cover and (cover.startswith("http") or not os.path.exists(str(cover))):
            local_path = ensure_cover_cached(track.path, cover)
            if local_path: track.cover_path = local_path

        # 2. Artist Avatar
        artist_thumb = data.get('artist_thumbnail') or track.artist_thumbnail
        if artist_thumb and str(artist_thumb).startswith("http"):
            artist_seed = (track.artist or "unknown").lower().strip()
            artist_key = f"artist_{hashlib.md5(artist_seed.encode()).hexdigest()}"
            
            local_artist = ensure_cover_cached(artist_key, artist_thumb)
            if local_artist:
                track.artist_thumbnail = local_artist
                if update_db: add_track_to_db(track.as_dict())

    # ------------------ PUBLIC API ------------------

    def set_global_playlist(self) -> List[Dict]:
        self.current_query = {"type": "global"}
        return self._apply_query()

    def set_playlist_from_folder(self, folder: str) -> List[Dict]:
        self.current_folder = folder
        
        # UI Multi-select logic
        if getattr(self, "set_playlist_mode", False):
            return self._handle_multi_select(folder)

        self.current_query = {"type": "playlist", "value": folder}
        return self._apply_query()

    def _handle_multi_select(self, folder: str) -> list:
        if not hasattr(self, "selected_playlists_for_set"):
            self.selected_playlists_for_set = []
            
        if folder in self.selected_playlists_for_set:
            self.selected_playlists_for_set.remove(folder)
            self.update_playlist_highlight(folder, False)
        else:
            self.selected_playlists_for_set.append(folder)
            self.update_playlist_highlight(folder, True)
        return []

    def get_playlist_dicts(self) -> List[Dict]:
        with self._lock:
            return [t.as_dict() for t in self.playlist]

    # ------------------ CORE QUERY PIPELINE ------------------

    def _apply_query(self) -> List[Dict]:
        with self._lock:
            if not self._library_ready:
                self.build_library_index()

            tracks = self._resolve_query(self.current_query)
            
            # Default Sorting: Folder -> Album -> Title
            tracks.sort(key=lambda t: (
                t.playlist or "000",
                t.album or "ZZZ",
                t.title or ""
            ))

            self.playlist = tracks 
            return [t.as_dict() for t in tracks]

    def _resolve_query(self, query: Dict) -> List[TrackInfo]:
        if not query or not self._library_ready:
            return []

        qtype = query.get("type")
        val = query.get("value")

        if qtype == "global":
            return list(self._library)
        if qtype == "playlist":
            return list(self._by_playlist.get(val, []))
        if qtype == "custom":
            res = []
            for p in val: res.extend(self._by_playlist.get(p, []))
            return res
        return []

    def _sync_current_index(self, playlist: List[TrackInfo]) -> int:
        if self.current_track:
            for i, t in enumerate(playlist):
                if t.path == self.current_track.path:
                    return i
        return -1