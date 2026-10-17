"""分散創造のイメージビデオ（MP4・GIF）を生成する。

使い方:
    pip install pillow numpy imageio-ffmpeg
    python tools/image_video/make_video.py

出力:
    media/image-video.mp4  … 音声付き（1280x720）
    media/image-video.gif  … README 表示用（音声なし・縮小）

ファイルの役割:
    timeline.py … 場面の時間割（映像と音楽が共有する）
    draw.py     … 描画の部品（キャラクター・文字・図形）
    scenes.py   … 各場面と、フレームの組み立て
    music.py    … 音楽と効果音の合成
"""

import subprocess
from pathlib import Path

import imageio_ffmpeg

from draw import H, W
from music import make_audio
from scenes import render_frame
from timeline import DURATION, FPS, FRAMES

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "media"
MP4 = OUT_DIR / "image-video.mp4"
GIF = OUT_DIR / "image-video.gif"
WAV = OUT_DIR / "_audio.wav"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    make_audio(WAV)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-i", str(WAV),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-preset", "slow",
         "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(MP4)],
        stdin=subprocess.PIPE)
    for n in range(FRAMES):
        proc.stdin.write(render_frame(n / FPS).tobytes())
        if n % FPS == 0:
            print(f"{n // FPS}s / {int(DURATION)}s")
    proc.stdin.close()
    proc.wait()
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(MP4),
         "-vf", "fps=12,scale=560:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];"
                "[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle",
         str(GIF)], check=True)
    WAV.unlink()
    print(f"出力: {MP4} / {GIF}")


if __name__ == "__main__":
    main()
