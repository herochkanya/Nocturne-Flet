# player.py

# MusicPlayer core module

from threading import RLock
import threading
from typing import Optional, Callable, List, Dict
from config import get_music_base_dir
from core.track_info import TrackInfo
from core.playlist import PlaylistManager
from core.playback import Playback
from core.equalizer import Equalizer
from core.modes import Modes

class MusicPlayer(PlaylistManager, Playback, Modes): # Додаємо Modes сюди
    def __init__(self):
        # Ініціалізація батьківських класів
        # PlaylistManager і Playback вже мають свої __init__
        self.base_dir = get_music_base_dir()
        self._lock = RLock()

        # --- СТАН ПЛЕЄРА ---
        self.current_track: Optional[TrackInfo] = None

        self.volume = 0.7
        
        self._stream = None 
        self._audio_data = None
        self._pos = 0
    
        self.playlist: List[TrackInfo] = []
        self.playlist_playback: List[str] = []
        self.current_index = -1
        self.is_paused = False
        self.is_playing = False
        
        self._track_change_callback: Optional[Callable[[Dict], None]] = None
        self._auto_next_enabled = True
        self._cycle_mode = 0
        self._shuffle_mode = False
        self._original_playlist: List[str] = []
        self.state_callback = None  

        self.current_query = None
        self._shuffle_cache = {}
        self.current_folder = None
        
        self._library = []
        self._by_author = {}
        self._by_playlist = {}
        self._library_ready = False 

        self.equalizer = Equalizer()

        self._track_listeners: List[Callable] = []

    def add_track_change_listener(self, cb: Callable[[Dict], None]):
        """Додає нового слухача події зміни треку."""
        if cb not in self._track_listeners:
            self._track_listeners.append(cb)

    def set_track_change_callback(self, cb: Callable[[Dict], None]):
        """Старий метод тепер просто додає слухача у список."""
        self.add_track_change_listener(cb)

    def _notify_track_changed(self, track_data: Dict):
        """Цей метод треба викликати там, де пісня реально змінюється (у Playback)"""
        for listener in self._track_listeners:
            try:
                listener(track_data)
            except Exception as e:
                print(f"Error notifying listener: {e}")
    
    def set_state_callback(self, callback):
        self.state_callback = callback
    
    def clear_library_index(self):
        with self._lock:
            self.base_dir = get_music_base_dir()
            self.current_query = None
            
            self.stop_engine()

            self.current_track = None
            self.current_index = -1
            self.is_playing = False
            self.is_paused = False
            
            self.playlist.clear()
            self.playlist_playback.clear()
            self._library.clear()
            self._by_author.clear()
            self._by_playlist.clear()
            
            self._library_ready = False
    
    def set_volume(self, volume: float):
        """Зберігаємо значення гучності."""
        self.volume = volume
        # Якщо у тебе в коді програвання є множник на self.volume, 
        # то звук реально стане тихішим.
        print(f"Volume set to: {self.volume}")