# bili-downloader

下载 B站视频并自动生成中文字幕（SRT），基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp) + [faster-whisper](https://github.com/SYSTRAN/faster-whisper)。

Download Bilibili videos and auto-generate Chinese subtitles using yt-dlp + faster-whisper.

---

## 功能 / Features

- 下载 B站视频（最高画质）/ Download at best quality
- 自动生成中文字幕（GPU 加速）/ Auto-generate Chinese subtitles via Whisper (CUDA)
- GUI 支持拖拽链接 / GUI with drag-and-drop URL support
- 已有字幕的视频自动跳过 / Skip already-subtitled videos
- 支持 Cookie 提升清晰度 / Cookie support for higher resolution

---

## 环境要求 / Requirements

- Python 3.10+
- NVIDIA GPU（字幕生成需要 CUDA / required for subtitle generation）

```bash
pip install yt-dlp faster-whisper imageio-ffmpeg
pip install tkinterdnd2   # 可选，启用拖拽 / optional, for drag-and-drop
```

---

## 使用方法 / Usage

### GUI（推荐 / Recommended）

```bash
python bili_download_gui.py
```

1. 填写**文件夹名**和**根目录** / Set folder name and root directory
2. 粘贴或拖入 B站链接 / Paste or drag Bilibili URLs
3. 选择 Whisper 模型 / Choose a Whisper model
4. 点击 **▶ 下载 + 字幕** / Click to download and generate subtitles

### 命令行 / Command line

编辑 `bili_download_and_subtitle.py` 顶部的配置区：

```python
FOLDER = "我的下载"       # 子文件夹名 / subfolder name
URLS = [
    "https://www.bilibili.com/video/BVxxxxxxxxxx",
]
MODEL = "large-v3"        # Whisper 模型 / model size
ROOT  = "D:/Downloads/bili"
```

然后运行 / Then run:

```bash
python bili_download_and_subtitle.py
```

### 输出结构 / Output structure

```
ROOT/
└── FOLDER/
    ├── video/
    │   └── 视频标题.mp4
    └── subtitle/
        └── 视频标题.srt
```

### Cookie（可选 / Optional）

将 Netscape 格式的 Cookie 文件（`.txt`）放到 `ROOT/cookie/` 目录下，可下载需要登录才能获取的高清画质。

Place a Netscape-format cookie file (`.txt`) in `ROOT/cookie/` to download higher-resolution videos that require login.

---

## Whisper 模型对比 / Model comparison

| 模型 / Model | 显存 / VRAM | 速度 / Speed | 准确度 / Accuracy |
|---|---|---|---|
| tiny | ~1 GB | 最快 / fastest | 低 / low |
| base | ~1 GB | 快 / fast | 较低 / low |
| small | ~2 GB | 快 / fast | 一般 / ok |
| medium | ~5 GB | 中 / medium | 好 / good |
| large-v2 | ~10 GB | 慢 / slow | 很好 / great |
| large-v3 | ~10 GB | 慢 / slow | 最好 / best |
