"""
B站视频下载 + 自动生成中文字幕（一键运行）

使用方法:
  1. 修改下方配置区的 FOLDER 和 URLS
  2. 终端运行: python bili_download_and_subtitle.py
  3. 视频下载到 <ROOT>/<FOLDER>/video/
  4. 字幕生成到 <ROOT>/<FOLDER>/subtitle/

依赖安装:
  pip install yt-dlp faster-whisper imageio-ffmpeg
"""

# ============================================================
#                    ↓↓↓ 在这里修改 ↓↓↓
# ============================================================

# 保存文件夹名（在 ROOT 下自动创建）
FOLDER = "我的下载"

# B站视频链接，每行一个
URLS = [
    # "https://www.bilibili.com/video/BVxxxxxxxxxx",
    # "https://www.bilibili.com/video/BVyyyyyyyyyy",
]

# Whisper 模型大小: tiny / base / small / medium / large-v2 / large-v3
MODEL = "large-v3"

# 视频根目录（会在这里创建 FOLDER 子目录）
ROOT = "D:/Downloads/bili"

# ============================================================
#                    ↑↑↑ 只需要改上面 ↑↑↑
# ============================================================

import sys
import os
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

CLASS_ROOT = Path(ROOT)

# 获取 ffmpeg 路径（通过 imageio-ffmpeg）
FFMPEG_PATH = None
try:
    import imageio_ffmpeg
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    pass


def find_cookie():
    cookie_dir = CLASS_ROOT / "cookie"
    if cookie_dir.exists():
        for f in cookie_dir.iterdir():
            if f.suffix == ".txt":
                return str(f)
    return None


def step1_download():
    import yt_dlp

    video_dir = CLASS_ROOT / FOLDER / "video"
    video_dir.mkdir(parents=True, exist_ok=True)
    (CLASS_ROOT / FOLDER / "subtitle").mkdir(exist_ok=True)

    cookie = find_cookie()
    if cookie:
        print(f"已找到 cookie: {Path(cookie).name}")
    else:
        print("未找到 cookie，将以未登录状态下载（可能限制清晰度）")

    opts = {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": str(video_dir / "%(title)s.%(ext)s"),
        "concurrent_fragment_downloads": 8,
    }
    if FFMPEG_PATH:
        opts["ffmpeg_location"] = FFMPEG_PATH
    if cookie:
        opts["cookiefile"] = cookie

    valid_urls = [u for u in URLS if "BV" in u]
    if not valid_urls:
        print("没有有效的视频链接，请先修改脚本顶部的 URLS")
        return False

    print(f"\n共 {len(valid_urls)} 个视频待下载\n")
    with yt_dlp.YoutubeDL(opts) as ydl:
        for i, url in enumerate(valid_urls, 1):
            print(f"[{i}/{len(valid_urls)}] {url}")
            ydl.download([url])

    print("\n所有视频下载完成！")
    return True


def step2_subtitle():
    # 加载 NVIDIA DLL（Windows + CUDA 环境）
    nvidia_dir = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    if nvidia_dir.exists():
        for bin_dir in nvidia_dir.rglob("bin"):
            if bin_dir.is_dir():
                os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")

    from faster_whisper import WhisperModel

    video_dir = CLASS_ROOT / FOLDER / "video"
    subtitle_dir = CLASS_ROOT / FOLDER / "subtitle"
    video_exts = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm", ".ts", ".m4v"}

    videos = sorted(f for f in video_dir.iterdir() if f.suffix.lower() in video_exts)
    if not videos:
        print("video/ 下没有视频文件")
        return

    to_process = []
    for v in videos:
        srt = subtitle_dir / v.with_suffix(".srt").name
        if srt.exists():
            print(f"跳过 (已有字幕): {v.name}")
        else:
            to_process.append((v, srt))

    if not to_process:
        print("所有视频已有字幕，无需处理。")
        return

    print(f"\n待转录: {len(to_process)} 个视频")
    print(f"加载模型: {MODEL} (cuda)\n")

    model = WhisperModel(MODEL, device="cuda", compute_type="float16")

    for video_path, srt_path in to_process:
        print(f"{'='*60}")
        print(f"转录: {video_path.name}")
        segments, info = model.transcribe(
            str(video_path), language="zh", beam_size=5,
            vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500),
        )
        print(f"时长: {info.duration:.1f}s")

        srt_lines = []
        for i, seg in enumerate(segments, start=1):
            h, m, s = int(seg.start//3600), int(seg.start%3600//60), int(seg.start%60)
            ms = int((seg.start - int(seg.start)) * 1000)
            start_ts = f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
            h, m, s = int(seg.end//3600), int(seg.end%3600//60), int(seg.end%60)
            ms = int((seg.end - int(seg.end)) * 1000)
            end_ts = f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
            text = seg.text.strip()
            srt_lines.append(f"{i}\n{start_ts} --> {end_ts}\n{text}\n")
            print(f"  [{start_ts} -> {end_ts}] {text}")

        srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
        print(f"已保存: {srt_path.name} ({len(srt_lines)} 条)\n")

    print("全部转录完成！")


if __name__ == "__main__":
    print(f"文件夹: {FOLDER}")
    print(f"目录: {CLASS_ROOT / FOLDER}\n")

    print("=" * 60)
    print("  第一步: 下载视频")
    print("=" * 60)
    step1_download()

    print("\n" + "=" * 60)
    print("  第二步: 生成字幕")
    print("=" * 60)
    step2_subtitle()
