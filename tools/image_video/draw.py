"""描画の部品。座標は 1280x720 の論理座標で受け取り、SS 倍の画像に描く。"""

import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
SS = 2  # 描画時の拡大率（縮小してなめらかにする）

BG = (255, 248, 235)
INK = (70, 55, 80)
WHITE = (255, 255, 255)
GRAY = (150, 150, 168)
CHAR_COLORS = [
    (255, 150, 185),  # もも
    (120, 220, 190),  # みんと
    (255, 210, 90),   # れもん
    (120, 190, 255),  # そら
    (190, 160, 255),  # ふじ
]
FONT_PATHS = ["C:/Windows/Fonts/YuGothB.ttc", "C:/Windows/Fonts/meiryob.ttc"]


# ---------------------------------------------------------------- 数値の補助

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


BOUNCE_FIRST_CONTACT = 1 / 2.75  # ease_out_bounce が初めて着地する割合


def ease_in_out(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def s(v):
    """論理座標を描画座標に変換する。"""
    return v * SS


# ---------------------------------------------------------------- 文字

@lru_cache(maxsize=128)
def font(size):
    for path in FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, max(1, int(size * SS)))
    return ImageFont.load_default()


def text_center(d, x, y, txt, size, color=INK):
    f = font(size)
    box = d.textbbox((0, 0), txt, font=f)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text((s(x) - w / 2 - box[0], s(y) - h / 2 - box[1]), txt, font=f, fill=color)


def text_pop(d, x, y, txt, size, t, color=INK, stagger=0.03, dur=0.35):
    """1 文字ずつ弾むように現れる見出し。t は表示開始からの経過時間。"""
    if t <= 0:
        return
    f = font(size)
    box = d.textbbox((0, 0), txt, font=f)
    h = box[3] - box[1]
    widths = [f.getlength(ch) for ch in txt]
    cx = s(x) - sum(widths) / 2
    top = s(y) - h / 2 - box[1]
    for i, (ch, w) in enumerate(zip(txt, widths)):
        p = (t - i * stagger) / dur
        if p > 0:
            dy = (1 - ease_out_back(p)) * s(size * 0.7)
            d.text((cx, top + dy), ch, font=f, fill=mix(BG, color, clamp(p * 2)))
        cx += w


def logo(d, x, y, size, t):
    """「分散創造」のロゴ。1 文字ずつ色違いのふち取り文字で降ってくる。"""
    txt = "分散創造"
    f = font(size)
    widths = [f.getlength(ch) for ch in txt]
    gap = s(size * 0.04)
    cx = s(x) - (sum(widths) + gap * (len(txt) - 1)) / 2
    box = d.textbbox((0, 0), txt, font=f)
    top = s(y) - (box[3] - box[1]) / 2 - box[1]
    for i, (ch, w) in enumerate(zip(txt, widths)):
        p = (t - i * 0.12) / 0.6
        if p > 0:
            dy = -(1 - ease_out_bounce(p)) * s(160)
            color = mix(CHAR_COLORS[i], INK, 0.15)
            d.text((cx + s(5), top + dy + s(6)), ch, font=f, fill=mix(BG, INK, 0.18))
            d.text((cx, top + dy), ch, font=f, fill=color, stroke_width=int(s(4)), stroke_fill=INK)
        cx += w + gap


# ---------------------------------------------------------------- 図形

def ellipse(d, cx, cy, rx, ry, fill, outline=None, width=0):
    d.ellipse([s(cx - rx), s(cy - ry), s(cx + rx), s(cy + ry)],
              fill=fill, outline=outline, width=int(s(width)))


def line(d, pts, color, width):
    d.line([(s(x), s(y)) for x, y in pts], fill=color, width=int(s(width)), joint="curve")
    r = width / 2
    for x, y in (pts[0], pts[-1]):
        ellipse(d, x, y, r, r, color)


def dashed(d, a, b, color, width=3, steps=14):
    for k in range(0, steps, 2):
        p0 = (lerp(a[0], b[0], k / steps), lerp(a[1], b[1], k / steps))
        p1 = (lerp(a[0], b[0], (k + 1) / steps), lerp(a[1], b[1], (k + 1) / steps))
        line(d, [p0, p1], color, width)


def star_points(cx, cy, r, rot=0.0):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.45
        a = rot - math.pi / 2 + i * math.pi / 5
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def star(d, cx, cy, r, rot=0.0, fill=(255, 225, 120), outline=INK):
    """素材（トーン模様の星）。"""
    if r < 1:
        return
    pts = [(s(x), s(y)) for x, y in star_points(cx, cy, r, rot)]
    d.polygon(pts, fill=fill, outline=outline, width=int(s(3)))
    for dx, dy in ((-0.2, -0.05), (0.15, 0.1), (0.0, 0.25)):
        ellipse(d, cx + dx * r, cy + dy * r, r * 0.07, r * 0.07, mix(fill, (200, 120, 40), 0.5))


def star_with_trail(d, pts_fn, k, r, rot):
    """動いている星に残像を付ける。pts_fn(k) は進み具合 k の位置。"""
    for j, back in enumerate((0.12, 0.08, 0.04)):
        if k - back > 0:
            x, y = pts_fn(k - back)
            star(d, x, y, r * (0.55 + j * 0.12), rot, fill=mix(BG, (255, 225, 120), 0.3 + j * 0.2), outline=mix(BG, INK, 0.3))
    x, y = pts_fn(k)
    star(d, x, y, r, rot)


def sparkle(d, cx, cy, r, color=(255, 230, 120)):
    if r < 0.5:
        return
    pts = [(cx, cy - r), (cx + r * 0.25, cy - r * 0.25), (cx + r, cy),
           (cx + r * 0.25, cy + r * 0.25), (cx, cy + r), (cx - r * 0.25, cy + r * 0.25),
           (cx - r, cy), (cx - r * 0.25, cy - r * 0.25)]
    d.polygon([(s(x), s(y)) for x, y in pts], fill=color)


def burst(d, cx, cy, t, dur=0.6, color=(255, 215, 110), count=10, reach=110):
    """着地や統合の瞬間に広がる波紋とキラキラ。t はその瞬間からの経過時間。"""
    if not 0 <= t < dur:
        return
    k = t / dur
    ring_r = 20 + ease_in_out(k) * reach
    ellipse(d, cx, cy, ring_r, ring_r * 0.9, None, mix(color, BG, k), 4 * (1 - k) + 1)
    for i in range(count):
        a = i * 2 * math.pi / count + 0.3
        rr = 20 + ease_in_out(k) * reach * 1.1
        sparkle(d, cx + math.cos(a) * rr, cy + math.sin(a) * rr, 12 * (1 - k), mix(color, BG, k * 0.5))


def dust(d, cx, ground, t, dur=0.35):
    """着地したときの土ぼこり。"""
    if not 0 <= t < dur:
        return
    k = t / dur
    for sx in (-1, 1):
        for j in range(3):
            x = cx + sx * (20 + ease_in_out(k) * (30 + j * 14))
            y = ground - 6 - j * 5 - k * 10
            r = (7 - j * 1.5) * (1 - k)
            ellipse(d, x, y, r, r, mix(BG, INK, 0.12))


# ---------------------------------------------------------------- キャラクター

def blob(d, cx, cy, r, color, t, squash=0.0, happy=False, look=0.0, sad=False, ground=None):
    """丸いキャラクター。squash が正なら横につぶれる。ground を渡すと足元に影を描く。"""
    w, h = r * (1 + squash), r * (1 - squash)
    if ground is not None:
        lift = clamp((ground - (cy + h)) / 120)
        sw = r * 0.85 * (1 - lift * 0.5)
        ellipse(d, cx, ground, sw, sw * 0.16, mix(BG, INK, 0.12 * (1 - lift * 0.6)))
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
    blush = mix(color, (255, 120, 150), 0.72)
    ellipse(d, cx - w * 0.55, cy + h * 0.18, w * 0.16, h * 0.1, blush)
    ellipse(d, cx + w * 0.55, cy + h * 0.18, w * 0.16, h * 0.1, blush)
    # 目
    blink = ((t + cx * 0.013) % 3.3) < 0.12
    ex, ey = w * 0.32, cy - h * 0.05
    for sx in (-1, 1):
        x = cx + sx * ex + look * w * 0.08
        if happy:
            d.arc([s(x - 9), s(ey - 6), s(x + 9), s(ey + 10)], 200, 340, fill=INK, width=int(s(4)))
        elif sad:
            ellipse(d, x, ey + 2, w * 0.07, h * 0.09, INK)
            line(d, [(x - sx * 10, ey - 18), (x + sx * 8, ey - 12)], INK, 3)
        elif blink:
            line(d, [(x - w * 0.1, ey), (x + w * 0.1, ey)], INK, 3)
        else:
            ellipse(d, x, ey, w * 0.11, h * 0.16, INK)
            ellipse(d, x - w * 0.03, ey - h * 0.06, w * 0.04, h * 0.05, WHITE)
    # 口
    my = cy + h * 0.25
    if happy:
        d.chord([s(cx - 10), s(my - 8), s(cx + 10), s(my + 10)], 0, 180, fill=(200, 70, 90), outline=INK, width=int(s(2)))
    elif sad:
        d.arc([s(cx - 8), s(my + 2), s(cx + 8), s(my + 12)], 200, 340, fill=INK, width=int(s(3)))
    else:
        d.arc([s(cx - 8), s(my - 6), s(cx + 8), s(my + 6)], 20, 160, fill=INK, width=int(s(3)))


def hop(t, period=0.5, height=18.0):
    """跳ねる動き。高さと着地時のつぶれを返す。"""
    p = (t % period) / period
    y = -math.sin(p * math.pi) * height
    squash = 0.18 * max(0.0, 1 - p * 6) - 0.08 * math.sin(p * math.pi)
    return y, squash


def tower(d, cx, cy, sc, t, sulk=False, label=True):
    """中央サーバー（悪役）。sulk でしょんぼり顔になる。"""
    w, h = 90 * sc, 120 * sc
    line(d, [(cx, cy - h), (cx, cy - h - 30 * sc)], INK, max(2, 4 * sc))
    lamp = (235, 70, 70) if int(t * 3) % 2 == 0 and not sulk else (150, 90, 90)
    ellipse(d, cx, cy - h - 34 * sc, 9 * sc, 9 * sc, lamp, INK, 2)
    d.rounded_rectangle([s(cx - w), s(cy - h), s(cx + w), s(cy + h)], radius=int(s(18 * sc)),
                        fill=GRAY, outline=INK, width=int(s(max(2, 4 * sc))))
    for k in range(3):
        y = cy + h * 0.25 + k * h * 0.22
        d.rounded_rectangle([s(cx - w * 0.7), s(y - h * 0.06), s(cx + w * 0.7), s(y + h * 0.06)],
                            radius=int(s(4 * sc)), fill=(120, 120, 138))
        ellipse(d, cx + w * 0.5, y, 4 * sc, 4 * sc, (140, 230, 140) if not sulk else (120, 140, 120))
    ey = cy - h * 0.45
    for sx in (-1, 1):
        x = cx + sx * w * 0.38
        if sulk:
            line(d, [(x - 12 * sc, ey), (x + 12 * sc, ey)], INK, max(2, 4 * sc))
        else:
            ellipse(d, x, ey + 4 * sc, 8 * sc, 8 * sc, INK)
            line(d, [(x - sx * 16 * sc, ey - 16 * sc), (x + sx * 12 * sc, ey - 4 * sc)], INK, max(2, 5 * sc))
    my = cy - h * 0.12
    d.arc([s(cx - 20 * sc), s(my), s(cx + 20 * sc), s(my + 22 * sc)], 200, 340, fill=INK, width=int(s(max(2, 4 * sc))))
    if label:
        text_center(d, cx, cy + h + 26 * sc, "中央サーバー", 26 * sc, INK)


def pc(d, x, y):
    """キャラクターが後ろに座る PC。(x, y) はキャラクターの足元あたり。"""
    d.rounded_rectangle([s(x - 50), s(y + 5), s(x + 50), s(y + 65)], radius=int(s(8)),
                        fill=(90, 90, 120), outline=INK, width=int(s(3)))
    d.rectangle([s(x - 42), s(y + 12), s(x + 42), s(y + 56)], fill=(200, 235, 255))
    d.rectangle([s(x - 12), s(y + 65), s(x + 12), s(y + 78)], fill=(90, 90, 120))


def stamp(d, cx, cy, txt, p):
    """赤いハンコ。p は押す動き（0〜1）。"""
    sc = 1.6 - 0.6 * ease_out_back(p)
    red = (220, 60, 70)
    w, h = 130 * sc, 50 * sc
    d.rounded_rectangle([s(cx - w), s(cy - h), s(cx + w), s(cy + h)], radius=int(s(10)),
                        outline=red, width=int(s(6)))
    text_center(d, cx, cy, txt, 48 * sc, red)


# ---------------------------------------------------------------- 背景

@lru_cache(maxsize=1)
def background():
    """淡いドット模様の背景。毎フレーム作り直さないように保持する。"""
    img = Image.new("RGB", (W * SS, H * SS), BG)
    d = ImageDraw.Draw(img)
    dot = mix(BG, INK, 0.06)
    for row, y in enumerate(range(18, H, 36)):
        for x in range(18 + (row % 2) * 18, W, 36):
            ellipse(d, x, y, 2, 2, dot)
    return img
