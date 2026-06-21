![Banner](https://github.com/user-attachments/assets/f1db33cf-2e71-4c38-8735-0ec0b21db542)

# Nocturne

A desktop music player focused on modern layout management, offline listening, and integrated media downloading. Built with Python and Flet.

---

## Features

* **Local Library Management**: Automated track indexing with metadata and artwork rendering.
* **Integrated Downloader**: Native support for asynchronous downloading via YouTube and SoundCloud URLs.
* **Media Controls**: Background thread playback handling with loop modes, shuffling, and global hotkeys.

---

## Screenshots

<p align="center">
  <img width="48%" alt="Nocturne Layout Selection" src="https://github.com/user-attachments/assets/a3cbd3bb-62fe-4461-b305-9fb4a888051e" />
  <img width="48%" alt="Nocturne Player UI" src="https://github.com/user-attachments/assets/2a4f6343-1fd4-48fc-9c34-23dcf8578cea" />
</p>

---

## Installation & Setup

### Environment Requirements
* Python 3.10 or higher
* Windows

### 1. Dependencies Installation
Clone the repository and install the required core packages:
```bash
pip install -r requirements.txt
```

### 2. FFmpeg Binary Configuration
The core playback engine requires local FFmpeg binaries for media decoding.
1. Download the release archive: [ffmpeg-release-essentials.zip](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip).
2. Extract the package contents.
3. Locate `ffmpeg.exe` and `ffprobe.exe` inside the extracted `bin/` directory.
4. Copy and paste both executables directly into the root `bin/` directory of this project (`Nocturne/bin/`).

### 3. Execution
Launch the application entry point:
```bash
python main.py
```

---

## Directory Structure

```
Nocturne/
│
├── bin/               # FFmpeg binaries and static resources
├── core/              # Playback controller, database, and backend logic
├── interface/         # PySide6 UI views and stylesheet configurations
├── config.py          # Global application parameters
├── main.py            # Application entry point
└── requirements.txt 
```

## Status & Development

Project is frozen for refactoring to PySide6. Check out the 'Nocturne' repository on GitHub to see the PySide version. 

* **GitHub**: [GitHub Issues](https://github.com/herochkanya/MusicPlayer)
* **Telegram**: Telegram [@This_username_is_already_taken_c](https://t.me/This_username_is_already_taken_c)

![Banner](https://github.com/user-attachments/assets/3da8af2c-b376-454b-ae0a-dc0511637476) 
