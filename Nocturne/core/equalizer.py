import math
import numpy as np
import scipy.signal as signal

class Equalizer:
    BANDS = [60, 150, 400, 1000, 2400, 15000]

    def __init__(self):
        self.gains = {freq: 0.0 for freq in self.BANDS}
        self.filters_state = {}
        # Кешуємо (b, a) для кожного фільтра
        self._coeffs_cache = {} 
        self._volume = 1.0

    def set_volume(self, volume_percent: int):
        self._volume = max(0.0, min(1.0, volume_percent / 100.0))

    def set_band(self, freq: int, gain_db: float):
        freq = int(freq)
        if freq in self.gains:
            # Якщо значення не змінилося, нічого не робимо
            if self.gains[freq] == float(gain_db):
                return
            self.gains[freq] = float(gain_db)
            # Очищуємо кеш лише для цієї частоти
            self._coeffs_cache.pop(freq, None)

    def _get_coefficients(self, freq, sr, gain_db):
        """Precompute biquad coefficients."""
        q = 1.0
        # Коригуємо формулу для gain (традиційна для peaking EQ)
        a_gain = 10**(gain_db / 40)
        w0 = 2 * math.pi * freq / sr
        alpha = math.sin(w0) / (2 * q)
        
        b0 = 1 + alpha * a_gain
        b1 = -2 * math.cos(w0)
        b2 = 1 - alpha * a_gain
        a0 = 1 + alpha / a_gain
        a1 = -2 * math.cos(w0)
        a2 = 1 - alpha / a_gain

        return (np.array([b0/a0, b1/a0, b2/a0], dtype='float32'), 
                np.array([1.0, a1/a0, a2/a0], dtype='float32'))

    def process(self, data: np.ndarray, samplerate: int) -> np.ndarray:
        # Працюємо безпосередньо з вхідним масивом, щоб не плодити копії
        # (sounddevice дозволяє модифікувати outdata на місці)
        
        for freq in self.BANDS:
            gain = self.gains[freq]
            
            # Навіть якщо gain == 0, краще прогнати фільтр, якщо він має стан,
            # або хоча б перерахувати коефіцієнти, щоб не було "сходинки"
            if gain == 0 and freq not in self.filters_state:
                continue

            # Отримуємо коефіцієнти з кешу
            if freq not in self._coeffs_cache:
                self._coeffs_cache[freq] = self._get_coefficients(freq, samplerate, gain)

            b, a = self._coeffs_cache[freq]

            # Ініціалізація стану для кожного каналу (stereo)
            if freq not in self.filters_state or self.filters_state[freq].shape[1] != data.shape[1]:
                self.filters_state[freq] = np.zeros((2, data.shape[1]), dtype='float32')

            # Обробка фільтром
            data, self.filters_state[freq] = signal.lfilter(
                b, a, data, axis=0, zi=self.filters_state[freq]
            )

        # Гучність
        if self._volume != 1.0:
            data *= self._volume
            
        return data # Вже float32