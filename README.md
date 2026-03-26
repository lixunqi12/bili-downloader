# bili-downloader

Download Bilibili videos and auto-generate Chinese subtitles (SRT) using [yt-dlp](https://github.com/yt-dlp/yt-dlp) + [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

## Features

- Download Bilibili videos at best quality
- Auto-generate Chinese subtitles via Whisper (GPU accelerated)
- GUI with drag-and-drop URL support
- Skip already-subtitled videos automatically
- Cookie support for higher resolution downloads

## Requirements

- Python 3.10+
- NVIDIA GPU (for subtitle generation with CUDA)

```bash
pip install yt-dlp faster-whisper imageio-ffmpeg
pip install tkinterdnd2   # optional, for drag-and-drop in GUI
```

## Usage

### GUI (recommended)

```bash
python bili_download_gui.py
```

1. Set the **folder name** and **root directory**
2. Paste or drag Bilibili URLs into the input box
3. Choose a Whisper model (larger = more accurate, slower)
4. Click **▶ 下载 + 字幕** to download and generate subtitles

### Command line

Edit the config section at the top of `bili_download_and_subtitle.py`:

```python
FOLDER = "my-videos"      # subfolder name under ROOT
URLS   = [
    "https://www.bilibili.com/video/BVxxxxxxxxxx",
]
MODEL  = "large-v3"       # whisper model
ROOT   = "D:/Downloads/bili"
```

Then run:

```bash
python bili_download_and_subtitle.py
```

### Output structure

```
ROOT/
└── FOLDER/
    ├── video/
    │   └── video_title.mp4
    └── subtitle/
        └── video_title.srt
```

### Cookie (optional)

To download higher-resolution videos that require login, place a Netscape-format cookie file (`.txt`) in `ROOT/cookie/`.

## Whisper models

| Model | VRAM | Speed | Accuracy |
|-------|------|-------|----------|
| tiny | ~1 GB | fastest | lowest |
| base | ~1 GB | fast | low |
| small | ~2 GB | fast | ok |
| medium | ~5 GB | medium | good |
| large-v2 | ~10 GB | slow | great |
| large-v3 | ~10 GB | slow | best |
