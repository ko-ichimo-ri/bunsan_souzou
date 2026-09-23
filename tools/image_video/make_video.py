"""分散創造のイメージビデオ（MP4・GIF）を生成する。

使い方:
    pip install pillow numpy imageio-ffmpeg
    python tools/image_video/make_video.py

出力:
    docs/media/image-video.mp4  … 音声付き（1280x720）
    docs/media/image-video.gif  … README 表示用（音声なし・縮小）
"""

import math
import random
import subprocess
import wave
from functools import lru_cache
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "docs" / "media"
MP4 = OUT_DIR / "image-video.mp4"
GIF = OUT_DIR / "image-video.gif"
WAV = OUT_DIR / "_audio.wav"

W, H = 1280, 720
SS = 2  # 描画時の拡大率（縮小してなめらかにする）
FPS = 24
DURATION = 25.0
FRAMES = int(FPS * DURATION)
SCENES = [0.0, 4.0, 10.0, 16.0, 21.0, DURATION]  # 各場面の開始時刻

BG = (255, 248, 235)
INK = (70, 55, 80)
WHITE = (255, 255, 255)
CHAR_COLORS = [
    (255, 150, 185),  # もも
    (120, 220, 190),  # みんと
    (255, 210, 90),   # れもん
    (120, 190, 255),  # そら
    (190, 160, 255),  # ふじ
]
FONT_PATHS = ["C:/Windows/Fonts/YuGothB.ttc", "C:/Windows/Fonts/meiryob.ttc"]


# ---------------------------------------------------------------- 補助関数

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def ease_out_back(t):
    t = clamp(t)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_out_bounce(t):
    t = clamp(t)
    n, d = 7.5625, 2.75
    if t < 1 / d:
        return n * t * t
    if t < 2 / d:
        t -= 1.5 / d
        return n * t * t + 0.75
    if t < 2.5 / d:
        t -= 2.25 / d
        return n * t * t + 0.9375
    t -= 2.625 / d
    return n * t * t + 0.984375


def ease_in_out(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def s(v):
    """論理座標を描画座標に変換する。"""
    return v * SS


@lru_cache(maxsize=64)
def font(size):
    for path in FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, int(size * SS))
    return ImageFont.load_default()


def text_center(d, x, y, txt, size, color=INK):
    f = font(size)
    box = d.textbbox((0, 0), txt, font=f)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text((s(x) - w / 2 - box[0], s(y) - h / 2 - box[1]), txt, font=f, fill=color)


def ellipse(d, cx, cy, rx, ry, fill, outline=None, width=0):
    d.ellipse([s(cx - rx), s(cy - ry), s(cx + rx), s(cy + ry)],
              fill=fill, outline=outline, width=int(s(width)))


def line(d, pts, color, width):
    d.line([(s(x), s(y)) for x, y in pts], fill=color, width=int(s(width)), joint="curve")
    r = width / 2
    for x, y in (pts[0], pts[-1]):
        ellipse(d, x, y, r, r, color)


def star_points(cx, cy, r, rot=0.0):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.45
        a = rot - math.pi / 2 + i * math.pi / 5
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def star(d, cx, cy, r, rot=0.0):
    """素材（トーン模様の星）。"""
    pts = [(s(x), s(y)) for x, y in star_points(cx, cy, r, rot)]
    d.polygon(pts, fill=(255, 225, 120), outline=INK, width=int(s(3)))
    for dx, dy in ((-0.2, -0.05), (0.15, 0.1), (0.0, 0.25)):
        ellipse(d, cx + dx * r, cy + dy * r, r * 0.07, r * 0.07, (240, 170, 60))


def sparkle(d, cx, cy, r, color=(255, 230, 120)):
    pts = [(cx, cy - r), (cx + r * 0.25, cy - r * 0.25), (cx + r, cy),
           (cx + r * 0.25, cy + r * 0.25), (cx, cy + r), (cx - r * 0.25, cy + r * 0.25),
           (cx - r, cy), (cx - r * 0.25, cy - r * 0.25)]
    d.polygon([(s(x), s(y)) for x, y in pts], fill=color)


def blob(d, cx, cy, r, color, t, squash=0.0, happy=False, look=0.0):
    """丸いキャラクター。squash が正なら横につぶれる。"""
    w, h = r * (1 + squash), r * (1 - squash)
    top = cy - h
    # 頭の芽
    sway = math.sin(t * 6 + cx) * 0.25
    tip = (cx + sway * 14, top - 18)
    line(d, [(cx, top + 2), tip], (90, 170, 90), 4)
    ellipse(d, tip[0] + 7, tip[1], 8, 5, (120, 200, 110), INK, 2)
    # 体
    ellipse(d, cx, cy, w, h, color, INK, 3)
    ellipse(d, cx - w * 0.35, cy - h * 0.45, w * 0.22, h * 0.14, mix(color, WHITE, 0.6))
    # ほっぺ
    blush = mix(color, (255, 110, 140), 0.55)
    ellipse(d, cx - w * 0.55, cy + h * 0.18, w * 0.16, h * 0.1, blush)
    ellipse(d, cx + w * 0.55, cy + h * 0.18, w * 0.16, h * 0.1, blush)
    # 目
    ex, ey = w * 0.32, cy - h * 0.05
    for sx in (-1, 1):
        x = cx + sx * ex + look * w * 0.08
        if happy:
            d.arc([s(x - 9), s(ey - 6), s(x + 9), s(ey + 10)], 200, 340, fill=INK, width=int(s(4)))
        else:
            ellipse(d, x, ey, w * 0.11, h * 0.16, INK)
            ellipse(d, x - w * 0.03, ey - h * 0.06, w * 0.04, h * 0.05, WHITE)
    # 口
    my = cy + h * 0.25
    if happy:
        d.chord([s(cx - 10), s(my - 8), s(cx + 10), s(my + 10)], 0, 180, fill=(200, 70, 90), outline=INK, width=int(s(2)))
    else:
        d.arc([s(cx - 8), s(my - 6), s(cx + 8), s(my + 6)], 20, 160, fill=INK, width=int(s(3)))


def hop(t, period=0.5, height=18.0):
    """跳ねる動き。高さと着地時のつぶれを返す。"""
    p = (t % period) / period
    y = -math.sin(p * math.pi) * height
    squash = 0.18 * max(0.0, 1 - p * 6) - 0.08 * math.sin(p * math.pi)
    return y, squash


# ---------------------------------------------------------------- 場面

def scene_title(d, t):
    title_p = ease_out_back((t - 0.2) / 0.7)
    if title_p > 0:
        text_center(d, 640, 210, "分散創造", 130 * title_p)
    sub = clamp((t - 1.0) / 0.5)
    if sub > 0:
        text_center(d, 640, 320, "ぶんさんそうぞう", 34, mix(BG, INK, sub))
    for i, color in enumerate(CHAR_COLORS):
        start = 0.8 + i * 0.25
        x = 240 + i * 200
        if t < start:
            continue
        p = (t - start) / 0.7
        y = lerp(-80, 540, ease_out_bounce(p))
        squash = 0.0
        if p >= 1:
            since = t - start - 0.7
            squash = 0.25 * math.exp(-since * 6) * math.cos(since * 25)
            y += math.sin(t * 5 + i) * 5
        blob(d, x, y, 60, color, t, squash, happy=p >= 1 and (t * 2 + i) % 3 < 1)


def scene_draw(d, t):
    # 左上の見出し
    text_center(d, 200, 110, "コマの中に", 40)
    text_center(d, 200, 170, "描く・消す・貼る", 40)
    # ページとコマ
    d.rectangle([s(400), s(40), s(880), s(680)], fill=WHITE, outline=INK, width=int(s(3)))
    p1 = (420, 60, 860, 330)
    p2 = (420, 350, 860, 660)
    for x0, y0, x1, y1 in (p1, p2):
        d.rectangle([s(x0), s(y0), s(x1), s(y1)], outline=INK, width=int(s(5)))
    text_center(d, 440, 80, "1", 22)
    text_center(d, 440, 370, "2", 22)

    # 線 A（波線）を描く
    wave_pts = [(460 + i * 6, 200 + math.sin(i * 0.35) * 45) for i in range(60)]
    a = int(len(wave_pts) * clamp((t - 0.4) / 2.0))
    if a >= 2:
        line(d, wave_pts[:a], INK, 6)
    # 線 B（ジグザグ）を描いて、消しゴムで消す
    zig = [(480 + i * 45, 290 - (i % 2) * 40) for i in range(9)]
    b = int(len(zig) * clamp((t - 2.5) / 1.0))
    erased = t > 4.3
    if b >= 2 and not erased:
        line(d, zig[:b], (220, 80, 110), 6)
    if 4.3 < t < 4.7:
        for k in range(6):
            a_ = k * math.pi / 3
            rr = 30 + (t - 4.3) * 150
            sparkle(d, 660 + math.cos(a_) * rr, 270 + math.sin(a_) * rr, 10, (255, 200, 220))

    # ペンを持つ もも（ペン先についていく）
    rest_tip = (900, 250)
    if t < 0.4:
        pen_tip = (lerp(rest_tip[0], wave_pts[0][0], t / 0.4), lerp(rest_tip[1], wave_pts[0][1], t / 0.4))
    elif t < 2.5:
        pen_tip = wave_pts[max(a - 1, 0)]
    elif t < 3.6:
        pen_tip = zig[max(b - 1, 0)]
    else:
        k = ease_in_out((t - 3.6) / 0.4)
        pen_tip = (lerp(zig[-1][0], rest_tip[0], k), lerp(zig[-1][1], rest_tip[1], k))
    hy, sq = hop(t, 0.6, 8)
    bx, by = pen_tip[0] + 60, pen_tip[1] - 55 + hy
    line(d, [(bx - 30, by + 25), pen_tip], (90, 90, 120), 8)
    ellipse(d, pen_tip[0], pen_tip[1], 5, 5, INK)
    blob(d, bx, by, 45, CHAR_COLORS[0], t, sq, happy=t > 2.4)

    # 消しゴムを持つ れもん（消しゴムと一緒に動く）
    home = (1000, 420)
    if t < 3.7:
        ex, ey = home
    elif t < 3.9:
        k = ease_in_out((t - 3.7) / 0.2)
        ex, ey = lerp(home[0], zig[0][0], k), lerp(home[1], 275, k)
    elif t < 4.3:
        ex, ey = lerp(zig[0][0], zig[-1][0], (t - 3.9) / 0.4), 275
    else:
        k = ease_in_out((t - 4.3) / 0.5)
        ex, ey = lerp(zig[-1][0], home[0], k), lerp(275, home[1], k)
    hy, sq = hop(t + 0.2, 0.5, 8)
    blob(d, ex + 45, ey - 45 + hy, 42, CHAR_COLORS[2], t, sq, happy=erased)
    d.rounded_rectangle([s(ex - 22), s(ey - 14), s(ex + 22), s(ey + 14)], radius=int(s(6)),
                        fill=(255, 190, 200), outline=INK, width=int(s(3)))

    # 素材を投げる みんと
    hy, sq = hop(t + 0.1, 0.55, 12)
    blob(d, 250, 560 + hy, 55, CHAR_COLORS[1], t, sq, happy=t > 5.4)
    throw = clamp((t - 4.6) / 0.8)
    if throw > 0:
        sx_, sy_ = 290, 520
        tx, ty = 640, 505
        x = lerp(sx_, tx, throw)
        y = lerp(sy_, ty, throw) - math.sin(throw * math.pi) * 180
        r = 60 * (0.5 + 0.5 * ease_out_back(throw)) if throw >= 1 else 35
        star(d, x, y, r, rot=(1 - throw) * 6)


def history_paths():
    common = [(180, 450), (330, 450), (480, 450)]
    main = common + [(640, 450), (800, 450), (980, 450), (1120, 450)]
    branch = common + [(560, 300), (640, 300), (800, 300), (980, 450), (1120, 450)]
    return main, branch


MERGE_AT = 4.5  # 分岐の場面で、2 人が合流点に着く時刻
BRANCH_END = 5.5


def path_length(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def traveled_on(pts, merge_index, t):
    """合流点に MERGE_AT、終点に BRANCH_END で着くように進んだ距離を返す。"""
    to_merge = path_length(pts[:merge_index + 1])
    if t < MERGE_AT:
        return to_merge * t / MERGE_AT
    return lerp(to_merge, path_length(pts), clamp((t - MERGE_AT) / (BRANCH_END - MERGE_AT)))


def path_point(pts, traveled):
    """折れ線上で、始点から距離 traveled の位置を返す。"""
    lens = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    traveled = clamp(traveled, 0.0, sum(lens))
    rest = traveled
    for (a, b), ln in zip(zip(pts, pts[1:]), lens):
        if rest <= ln:
            k = rest / ln if ln else 0
            return (lerp(a[0], b[0], k), lerp(a[1], b[1], k)), traveled
        rest -= ln
    return pts[-1], traveled


def draw_trail(d, pts, traveled, color):
    pos, dist = path_point(pts, traveled)
    trail = [pts[0]]
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        ln = math.dist(a, b)
        if acc + ln <= dist:
            trail.append(b)
        acc += ln
    trail.append(pos)
    line(d, trail, color, 10)
    reached = 0.0
    for a, b in zip([pts[0]] + pts, pts):
        reached += math.dist(a, b)
        if reached <= dist + 1:
            ellipse(d, b[0], b[1], 16, 16, WHITE, INK, 4)
    return pos


def scene_branch(d, t):
    merged = t > MERGE_AT
    caption = "統合！" if merged else "履歴系統を 分岐 して…"
    text_center(d, 640, 110, caption, 48)
    main, branch = history_paths()
    pos_b = draw_trail(d, branch, traveled_on(branch, 6, t), mix(CHAR_COLORS[4], INK, 0.2))
    pos_m = draw_trail(d, main, traveled_on(main, 5, t), mix(CHAR_COLORS[3], INK, 0.2))
    if merged:
        k = clamp((t - MERGE_AT) / 0.8)
        for i in range(10):
            a = i * math.pi / 5 + t
            rr = 40 + k * 120
            sparkle(d, 980 + math.cos(a) * rr, 450 + math.sin(a) * rr, 16 * (1 - k * 0.6))
    together = clamp((t - MERGE_AT + 0.2) / 0.3) * 32
    hy, sq = hop(t, 0.45, 14)
    blob(d, pos_m[0] - together, pos_m[1] - 60 + hy, 46, CHAR_COLORS[3], t, sq, happy=merged)
    hy, sq = hop(t + 0.2, 0.45, 14)
    blob(d, pos_b[0] + together, pos_b[1] - 60 + hy, 46, CHAR_COLORS[4], t, sq, happy=merged)
    text_center(d, 360, 610, "別案をためして", 30)
    text_center(d, 920, 610, "いいとこどり", 30)


def pc_nodes():
    return [(640 + math.cos(-math.pi / 2 + i * 2 * math.pi / 5) * 250,
             400 + math.sin(-math.pi / 2 + i * 2 * math.pi / 5) * 210) for i in range(5)]


HOPS = [0, 2, 4, 1, 3]


def scene_p2p(d, t):
    text_center(d, 640, 60, "素材は、みんなで手渡し", 44)
    nodes = pc_nodes()
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            steps = 14
            for k in range(0, steps, 2):
                p0 = (lerp(a[0], b[0], k / steps), lerp(a[1], b[1], k / steps))
                p1 = (lerp(a[0], b[0], (k + 1) / steps), lerp(a[1], b[1], (k + 1) / steps))
                line(d, [p0, p1], (200, 190, 200), 3)
    text_center(d, 640, 410, "ピアどうしで直接", 28, (150, 130, 150))

    hop_len = 0.9
    idx = int(t // hop_len)
    has_copy = set(HOPS[:min(idx + 1, len(HOPS))])
    for i, (x, y) in enumerate(nodes):
        d.rounded_rectangle([s(x - 50), s(y + 5), s(x + 50), s(y + 65)], radius=int(s(8)),
                            fill=(90, 90, 120), outline=INK, width=int(s(3)))
        d.rectangle([s(x - 42), s(y + 12), s(x + 42), s(y + 56)], fill=(200, 235, 255))
        d.rectangle([s(x - 12), s(y + 65), s(x + 12), s(y + 78)], fill=(90, 90, 120))
        got = i in has_copy
        hy, sq = hop(t + i * 0.13, 0.5, 16 if got else 6)
        blob(d, x, y - 30 + hy, 40, CHAR_COLORS[i], t, sq, happy=got)
        if got:
            star(d, x + 40, y - 70, 16, rot=t * 2 + i)

    if idx < len(HOPS) - 1:
        a, b = nodes[HOPS[idx]], nodes[HOPS[idx + 1]]
        k = (t % hop_len) / hop_len
        x = lerp(a[0], b[0], k)
        y = lerp(a[1], b[1], k) - 40 - math.sin(k * math.pi) * 120
        star(d, x, y, 28, rot=t * 5)


CONFETTI = [(random.Random(i).uniform(0, W), random.Random(i + 99).uniform(-H, 0),
             random.Random(i + 7).uniform(60, 160), random.Random(i + 3).choice(CHAR_COLORS))
            for i in range(90)]


def scene_finale(d, t):
    for x0, y0, speed, color in CONFETTI:
        y = (y0 + t * speed * 2.2) % (H + 40) - 20
        x = x0 + math.sin(t * 3 + x0) * 20
        d.rectangle([s(x - 5), s(y - 3), s(x + 5), s(y + 3)], fill=color)
    tp = ease_out_back(t / 0.6)
    text_center(d, 640, 170, "分散創造", 120 * max(tp, 0.01))
    if t > 0.7:
        text_center(d, 640, 290, "描く。分岐する。", 44, mix(BG, INK, clamp((t - 0.7) / 0.4)))
    if t > 1.3:
        text_center(d, 640, 350, "素材と拡張機能は、誰にも消されない。", 36, mix(BG, INK, clamp((t - 1.3) / 0.4)))
    rng = random.Random(5)
    for i, color in enumerate(CHAR_COLORS):
        period = rng.uniform(0.35, 0.55)
        phase = rng.uniform(0, 1)
        hy, sq = hop(t + phase, period, rng.uniform(40, 80))
        x = 240 + i * 200 + math.sin(t * 4 + i) * 25
        blob(d, x, 560 + hy, 58, color, t, sq, happy=True, look=math.sin(t * 3 + i))


SCENE_FUNCS = [scene_title, scene_draw, scene_branch, scene_p2p, scene_finale]


def render_frame(n):
    t = n / FPS
    k = max(i for i, start in enumerate(SCENES[:-1]) if t >= start)
    lt = t - SCENES[k]
    img = Image.new("RGB", (W * SS, H * SS), BG)
    d = ImageDraw.Draw(img)
    SCENE_FUNCS[k](d, lt)
    img = img.resize((W, H), Image.LANCZOS)
    # 場面の切り替わりで背景色にフェード
    edge = min(t - SCENES[k], SCENES[k + 1] - t)
    fade = 1 - clamp(edge / 0.2)
    if k == 0 and t < 0.2:
        fade = 0.0
    if fade > 0:
        img = Image.blend(img, Image.new("RGB", (W, H), BG), fade)
    return img


# ---------------------------------------------------------------- 音声

SR = 44100
BPM = 120
BEAT = 60 / BPM


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env(n, attack=0.005, release=0.08):
    t = np.arange(n) / SR
    a = np.clip(t / attack, 0, 1)
    r = np.clip((n / SR - t) / release, 0, 1)
    return a * r


def square(freq, dur, duty=0.25):
    n = int(dur * SR)
    ph = (np.arange(n) * freq / SR) % 1.0
    return np.where(ph < duty, 1.0, -1.0) * env(n)


def triangle(freq, dur):
    n = int(dur * SR)
    ph = (np.arange(n) * freq / SR) % 1.0
    return (4 * np.abs(ph - 0.5) - 1) * env(n, 0.005, 0.05)


def add(buf, sig, at, gain):
    i = int(at * SR)
    j = min(len(buf), i + len(sig))
    if i < len(buf):
        buf[i:j] += sig[:j - i] * gain


def pop_sfx():
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    freq = 400 + 1400 * t / 0.12
    return np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 30)


def make_audio():
    total = int(DURATION * SR)
    buf = np.zeros(total)
    chords = [(60, 64, 67), (55, 59, 62), (57, 60, 64), (53, 57, 60)]  # C G Am F
    rng = random.Random(42)
    bar = 4 * BEAT
    motif = [1, 0, 1, 1, 0, 1, 1, 1]  # 8 分音符ごとの発音
    for b in range(int(DURATION / bar) + 1):
        start = b * bar
        chord = chords[b % 4]
        # ベース
        for k in range(4):
            add(buf, triangle(midi_hz(chord[0] - 12), BEAT * 0.9), start + k * BEAT, 0.28)
        # キック
        for k in (0, 2):
            n = int(0.15 * SR)
            tt = np.arange(n) / SR
            kick = np.sin(2 * np.pi * np.cumsum(120 * np.exp(-tt * 25) + 45) / SR) * np.exp(-tt * 18)
            add(buf, kick, start + k * BEAT, 0.35)
        # ハイハット
        for k in range(8):
            n = int(0.03 * SR)
            hat = np.random.default_rng(b * 8 + k).uniform(-1, 1, n) * np.exp(-np.arange(n) / SR * 120)
            add(buf, hat, start + k * BEAT / 2, 0.06)
        # メロディ（和音の音と五音音階から選ぶ）
        if start >= 0.5:
            scale = [c + 12 for c in chord] + [chord[0] + 24, chord[0] + 14]
            for k, on in enumerate(motif):
                if on and rng.random() < 0.9:
                    note = rng.choice(scale)
                    add(buf, square(midi_hz(note), BEAT / 2 * 0.85), start + k * BEAT / 2, 0.12)
    # 効果音：タイトルの着地
    for i in range(5):
        add(buf, pop_sfx(), 0.8 + i * 0.25 + 0.7 * 0.36, 0.35)
    # 効果音：統合のキラキラ
    for k, note in enumerate([84, 88, 91, 96, 100]):
        add(buf, square(midi_hz(note), 0.12, 0.5), SCENES[2] + MERGE_AT + k * 0.06, 0.12)
    # 効果音：素材の受け渡し
    for k in range(len(HOPS) - 1):
        add(buf, pop_sfx(), SCENES[3] + (k + 1) * 0.9, 0.3)
    # 締めの和音
    for note in (72, 76, 79, 84):
        add(buf, square(midi_hz(note), 1.6, 0.5) * np.linspace(1, 0, int(1.6 * SR)), DURATION - 2.2, 0.08)
    # 全体のフェード
    fade = np.ones(total)
    fi, fo = int(0.3 * SR), int(1.0 * SR)
    fade[:fi] = np.linspace(0, 1, fi)
    fade[-fo:] = np.linspace(1, 0, fo)
    buf *= fade
    buf = buf / np.max(np.abs(buf)) * 0.8
    pcm = (buf * 32767).astype(np.int16)
    with wave.open(str(WAV), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- 出力

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    make_audio()
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-i", str(WAV),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "24", "-preset", "medium",
         "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(MP4)],
        stdin=subprocess.PIPE)
    for n in range(FRAMES):
        proc.stdin.write(render_frame(n).tobytes())
        if n % FPS == 0:
            print(f"{n // FPS}s / {int(DURATION)}s")
    proc.stdin.close()
    proc.wait()
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(MP4),
         "-vf", "fps=12,scale=560:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=4",
         str(GIF)], check=True)
    WAV.unlink()
    print(f"出力: {MP4} / {GIF}")


if __name__ == "__main__":
    main()
