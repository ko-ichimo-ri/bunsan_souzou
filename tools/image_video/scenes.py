"""イメージビデオの各場面と、フレームの組み立て。

各場面の関数は (img, d, t) を受け取る。t は場面の開始からの経過時間[秒]。
音楽と同期させる瞬間（着地・統合など）は、場面ごとの定数として公開する。
"""

import math
import random

from PIL import Image, ImageChops, ImageDraw

from draw import (BG, BOUNCE_FIRST_CONTACT, CHAR_COLORS, H, INK, W, WHITE, background, blob, burst, clamp,
                  dashed, dust, ease_in_out, ease_out_back, ease_out_bounce, ellipse, hop, lerp, line, logo,
                  mix, pc, s, stamp, star, star_with_trail, text_center, text_pop, tower)
from timeline import LENGTH, SCENE_INDEX, SCENE_PLAN, scene_at

# ---------------------------------------------------------------- 1. タイトル

TITLE_DROPS = [0.8 + i * 0.25 for i in range(5)]
TITLE_DROP_DUR = 0.7
TITLE_LANDS = [at + TITLE_DROP_DUR * BOUNCE_FIRST_CONTACT for at in TITLE_DROPS]


def scene_title(img, d, t):
    logo(d, 640, 205, 130, t - 0.15)
    text_pop(d, 640, 318, "ぶんさんそうぞう", 34, t - 1.0, mix(INK, BG, 0.25), stagger=0.05)
    ground = 600
    for i, color in enumerate(CHAR_COLORS):
        x = 240 + i * 200
        if t < TITLE_DROPS[i]:
            continue
        p = (t - TITLE_DROPS[i]) / TITLE_DROP_DUR
        y = lerp(-80, 540, ease_out_bounce(p))
        squash = 0.0
        landed = p >= 1
        if landed:
            since = t - TITLE_DROPS[i] - TITLE_DROP_DUR
            squash = 0.25 * math.exp(-since * 6) * math.cos(since * 25)
            y += math.sin(t * 5 + i) * 5
        dust(d, x, ground, t - TITLE_LANDS[i])
        blob(d, x, y, 60, color, t, squash, happy=landed and (t * 2 + i) % 3 < 1,
             look=(640 - x) / 640, ground=ground)


# ---------------------------------------------------------------- 2. 描く

DRAW_THROW_AT = 4.6
DRAW_THROW_DUR = 0.8


def scene_draw(img, d, t):
    text_pop(d, 200, 110, "コマの中に", 40, t - 0.1)
    text_pop(d, 200, 170, "描く・消す・貼る", 40, t - 0.35)
    d.rectangle([s(400), s(40), s(880), s(680)], fill=WHITE, outline=INK, width=int(s(3)))
    p1 = (420, 60, 860, 330)
    p2 = (420, 350, 860, 660)
    for x0, y0, x1, y1 in (p1, p2):
        d.rectangle([s(x0), s(y0), s(x1), s(y1)], outline=INK, width=int(s(5)))
    text_center(d, 440, 80, "1", 22)
    text_center(d, 440, 370, "2", 22)

    wave_pts = [(460 + i * 6, 200 + math.sin(i * 0.35) * 45) for i in range(60)]
    a = int(len(wave_pts) * clamp((t - 0.4) / 2.0))
    if a >= 2:
        line(d, wave_pts[:a], INK, 6)
    zig = [(480 + i * 45, 290 - (i % 2) * 40) for i in range(9)]
    b = int(len(zig) * clamp((t - 2.5) / 1.0))
    erased = t > 4.3
    if b >= 2 and not erased:
        line(d, zig[:b], (220, 80, 110), 6)
    burst(d, 660, 275, t - 4.3, 0.5, (255, 190, 215), count=8, reach=90)

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
    blob(d, bx, by, 45, CHAR_COLORS[0], t, sq, happy=t > 2.4, look=-0.6)

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
    blob(d, ex + 45, ey - 45 + hy, 42, CHAR_COLORS[2], t, sq, happy=erased, look=-0.5)
    d.rounded_rectangle([s(ex - 22), s(ey - 14), s(ex + 22), s(ey + 14)], radius=int(s(6)),
                        fill=(255, 190, 200), outline=INK, width=int(s(3)))

    # 素材を投げる みんと
    hy, sq = hop(t + 0.1, 0.55, 12)
    blob(d, 250, 560 + hy, 55, CHAR_COLORS[1], t, sq, happy=t > DRAW_THROW_AT + DRAW_THROW_DUR,
         look=0.7, ground=620)
    throw = clamp((t - DRAW_THROW_AT) / DRAW_THROW_DUR)
    landed_t = t - DRAW_THROW_AT - DRAW_THROW_DUR
    if throw > 0:
        def pos(k):
            return lerp(290, 640, k), lerp(520, 505, k) - math.sin(k * math.pi) * 180
        if throw < 1:
            star_with_trail(d, pos, throw, 35, (1 - throw) * 6)
        else:
            burst(d, 640, 505, landed_t, 0.5)
            star(d, 640, 505, 60 * (0.5 + 0.5 * ease_out_back(landed_t / 0.4)), rot=0.0)


# ---------------------------------------------------------------- 3. コマ割りと中身

PANEL_LAYOUT_A = [(420, 110, 860, 380), (420, 400, 860, 670)]
PANEL_LAYOUT_B = [(420, 110, 860, 300), (560, 320, 860, 670)]
PANELS_MOVE_AT = 0.6


def heart_point(u, cx, cy, sc):
    return (cx + 16 * math.sin(u) ** 3 * sc,
            cy - (13 * math.cos(u) - 5 * math.cos(2 * u) - 2 * math.cos(3 * u) - math.cos(4 * u)) * sc)


def paste_clipped(img, frame, draw_content):
    """コマの枠の範囲だけに中身を描いて貼る。draw_content(dd, cx, cy) は枠の中心を原点に描く。"""
    x0, y0, x1, y1 = frame
    layer = Image.new("RGB", (int(s(x1 - x0)), int(s(y1 - y0))), WHITE)
    draw_content(ImageDraw.Draw(layer), (x1 - x0) / 2, (y1 - y0) / 2)
    img.paste(layer, (int(s(x0)), int(s(y0))))


def wave_points(cx, cy, sc=1.0):
    return [(cx + (-150 + i * 5) * sc, cy + math.sin(i * 0.35) * 35 * sc) for i in range(61)]


def scene_panels(img, d, t):
    text_pop(d, 640, 50, "コマ割りと中身は、別々に管理", 42, t - 0.1)
    d.rectangle([s(400), s(90), s(880), s(690)], fill=WHITE, outline=INK, width=int(s(3)))
    k = ease_in_out((t - PANELS_MOVE_AT) / 1.6)
    frames = [tuple(lerp(a, b, k) for a, b in zip(fa, fb)) for fa, fb in zip(PANEL_LAYOUT_A, PANEL_LAYOUT_B)]
    heart_n = int(60 * clamp((t - 0.8) / 2.2))

    def content1(dd, cx, cy):
        line(dd, wave_points(cx - 40, cy - 10), INK, 6)
        if heart_n >= 2:
            line(dd, [heart_point(2 * math.pi * i / 60, cx + 130, cy - 20, 2.5) for i in range(heart_n)],
                 (230, 90, 130), 6)

    def content2(dd, cx, cy):
        star(dd, cx, cy - 20, 70, rot=0.2)
        for gx in range(-120, 130, 30):
            line(dd, [(cx + gx, cy + 110), (cx + gx + 8, cy + 90)], (110, 170, 110), 4)

    paste_clipped(img, frames[0], content1)
    paste_clipped(img, frames[1], content2)
    for x0, y0, x1, y1 in frames:
        d.rectangle([s(x0), s(y0), s(x1), s(y1)], outline=INK, width=int(s(5)))
    x0, y0, x1, y1 = frames[1]
    moving = 0 < k < 1
    for hx, hy_ in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        r = 9 if moving else 7
        d.rectangle([s(hx - r), s(hy_ - r), s(hx + r), s(hy_ + r)], fill=(120, 190, 255), outline=INK, width=int(s(2)))
    hy, sq = hop(t, 0.5, 8)
    blob(d, x0 - 50, y1 - 30 + hy, 42, CHAR_COLORS[3], t, sq, happy=t > 2.4, look=0.6)
    f0 = frames[0]
    fc = ((f0[0] + f0[2]) / 2, (f0[1] + f0[3]) / 2)
    tip = heart_point(2 * math.pi * max(heart_n - 1, 0) / 60, fc[0] + 130, fc[1] - 20, 2.5)
    hy, sq = hop(t + 0.3, 0.6, 6)
    bx, by = tip[0] + 55, tip[1] - 45 + hy
    line(d, [(bx - 28, by + 22), tip], (90, 90, 120), 8)
    blob(d, bx, by, 40, CHAR_COLORS[0], t, sq, happy=t > 3.1, look=-0.6)
    text_pop(d, 200, 330, "枠を動かしても", 32, t - 2.3)
    text_pop(d, 200, 380, "絵はそのまま", 32, t - 2.5)
    text_pop(d, 1090, 330, "枠と絵を", 32, t - 3.1)
    text_pop(d, 1090, 380, "同時に作業できる", 32, t - 3.3)


# ---------------------------------------------------------------- 4. 履歴の良さ

REVERT_AT = 1.7
DIFF_AT = 2.2


def mini_panel(d, x0, y0, x1, y1, scribble=False, highlight=False, t=0.0):
    """1 コマ分の絵。highlight は差分として光らせる線。"""
    d.rectangle([s(x0), s(y0), s(x1), s(y1)], fill=WHITE, outline=INK, width=int(s(4)))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    sc = (x1 - x0) / 400
    line(d, wave_points(cx - 30 * sc, cy - 40 * sc, sc), INK, 6 * sc + 1)
    star(d, cx + 110 * sc, cy + 70 * sc, 36 * sc, rot=0.3)
    if scribble:
        rng = random.Random(3)
        pts = [(cx - 120 * sc + i * 12 * sc, cy + 60 * sc + rng.uniform(-40, 40) * sc) for i in range(18)]
        line(d, pts, (220, 70, 80), 5 * sc + 1)
    if highlight:
        pts = [(cx - 150 * sc + i * 8 * sc, cy + 50 * sc + math.sin(i * 0.3) * 12 * sc) for i in range(20)]
        glow = 0.5 + 0.5 * math.sin(t * 8)
        line(d, pts, mix((255, 240, 190), (255, 210, 120), glow), 18 * sc)
        line(d, pts, (240, 140, 40), 6 * sc)


def scene_history(img, d, t):
    text_pop(d, 640, 50, "履歴があるから", 44, t - 0.1)
    reverted = t > REVERT_AT
    xs = [170, 270, 370]
    node_x = 470
    line(d, [(xs[0], 130), (xs[-1] if not reverted else lerp(xs[-1], node_x, clamp((t - REVERT_AT) / 0.2)), 130)],
         (150, 140, 160), 6)
    for i, x in enumerate(xs):
        fill = (255, 200, 205) if i == 2 else WHITE
        ellipse(d, x, 130, 20, 20, fill, INK, 4)
        text_center(d, x, 130, str(i + 1), 20)
    if reverted:
        r = 20 * ease_out_back((t - REVERT_AT - 0.1) / 0.3)
        if r > 1:
            ellipse(d, node_x, 130, r, r, (255, 240, 200), INK, 4)
            text_center(d, node_x, 130, "戻", 20 * r / 20)
    mini_panel(d, 120, 180, 520, 540, scribble=not reverted)
    burst(d, 320, 360, t - REVERT_AT, 0.6, (255, 220, 140), count=12, reach=180)
    pressed = REVERT_AT - 0.3 < t < REVERT_AT + 0.1
    by = 280 + (4 if pressed else 0)
    d.rounded_rectangle([s(560), s(by - 24), s(680), s(by + 24)], radius=int(s(12)),
                        fill=(255, 225, 150) if pressed else (255, 240, 200), outline=INK, width=int(s(3)))
    text_center(d, 620, by, "戻す", 26)
    hy, sq = hop(t, 0.55, 8)
    blob(d, 620, 400 + hy, 44, CHAR_COLORS[2], t, sq, happy=reverted, sad=not reverted, look=-0.5, ground=445)
    text_pop(d, 320, 600, "失敗しても戻せる", 32, t - REVERT_AT - 0.1)
    if t > DIFF_AT:
        k = ease_out_back((t - DIFF_AT) / 0.5)
        off = (1 - k) * 40
        text_center(d, 830, 170 + off, "前", 26)
        text_center(d, 1090, 170 + off, "後", 26)
        mini_panel(d, 730, 195 + off, 930, 375 + off)
        mini_panel(d, 990, 195 + off, 1190, 375 + off, highlight=True, t=t)
        text_center(d, 1090, 405 + off, "差分", 26, (230, 130, 40))
        hy, sq = hop(t + 0.2, 0.5, 10)
        blob(d, 960, 500 + hy, 44, CHAR_COLORS[1], t, sq, happy=True, look=0.6, ground=545)
    text_pop(d, 960, 600, "差分がひと目でわかる", 32, t - DIFF_AT - 0.6)


# ---------------------------------------------------------------- 5. 分岐と統合

MERGE_AT = 4.2
BRANCH_END = 5.2
BRANCH_MAIN = [(180, 450), (330, 450), (480, 450), (640, 450), (800, 450), (980, 450), (1120, 450)]
BRANCH_SIDE = [(180, 450), (330, 450), (480, 450), (560, 300), (640, 300), (800, 300), (980, 450), (1120, 450)]


def path_length(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def traveled_on(pts, merge_index, t):
    """合流点に MERGE_AT、終点に BRANCH_END で着くように進んだ距離を返す。"""
    to_merge = path_length(pts[:merge_index + 1])
    if t < MERGE_AT:
        return to_merge * ease_in_out(t / MERGE_AT) if t > 0 else 0.0
    return lerp(to_merge, path_length(pts), ease_in_out((t - MERGE_AT) / (BRANCH_END - MERGE_AT)))


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


def scene_branch(img, d, t):
    merged = t > MERGE_AT
    if merged:
        text_pop(d, 640, 110, "統合！", 56, t - MERGE_AT)
    else:
        text_pop(d, 640, 110, "履歴系統を 分岐 して…", 48, t - 0.1)
    pos_b = draw_trail(d, BRANCH_SIDE, traveled_on(BRANCH_SIDE, 6, t), mix(CHAR_COLORS[4], INK, 0.2))
    pos_m = draw_trail(d, BRANCH_MAIN, traveled_on(BRANCH_MAIN, 5, t), mix(CHAR_COLORS[3], INK, 0.2))
    burst(d, 980, 450, t - MERGE_AT, 0.8, count=12, reach=150)
    together = clamp((t - MERGE_AT + 0.2) / 0.3) * 32
    hy, sq = hop(t, 0.45, 14)
    blob(d, pos_m[0] - together, pos_m[1] - 60 + hy, 46, CHAR_COLORS[3], t, sq, happy=merged, look=0.6)
    hy, sq = hop(t + 0.2, 0.45, 14)
    blob(d, pos_b[0] + together, pos_b[1] - 60 + hy, 46, CHAR_COLORS[4], t, sq, happy=merged, look=0.6)
    text_pop(d, 360, 580, "別案をためして", 30, t - 1.2)
    text_pop(d, 920, 580, "いいとこどり", 30, t - MERGE_AT - 0.2)


# ---------------------------------------------------------------- 6. サーバー停止

OFFLINE_STOP = 0.8
OFFLINE_ADDS = [1.2, 1.8, 2.4, 3.0]


def scene_offline(img, d, t):
    text_pop(d, 640, 45, "分散型：履歴は一人ひとりの手元に", 40, t - 0.1)
    stopped = t > OFFLINE_STOP
    tw = (640, 215)
    for x in (380, 900):
        dashed(d, (tw[0], tw[1] + 90), (x, 420), mix((190, 180, 195), BG, clamp((t - OFFLINE_STOP) / 0.5)), 3, 16)
    tower(d, tw[0], tw[1], 0.7, t, sulk=stopped)
    if stopped:
        k = ease_out_back((t - OFFLINE_STOP) / 0.3)
        d.rounded_rectangle([s(760), s(150 - 24 * k), s(890), s(150 + 24 * k)], radius=int(s(8)),
                            fill=(235, 235, 240), outline=INK, width=int(s(3)))
        text_center(d, 825, 150, "停止中", 28 * max(k, 0.05))
        for i in range(3):
            p = ((t - OFFLINE_STOP) * 0.8 + i / 3) % 1
            text_center(d, 700 + p * 50 + i * 12, 150 - p * 70, "Z", 18 + i * 6, mix(INK, BG, p))
    added = sum(1 for at in OFFLINE_ADDS if t > at)
    for i, x in enumerate((380, 900)):
        color = CHAR_COLORS[3 + i]
        pc(d, x, 430)
        hy, sq = hop(t + i * 0.25, 0.5, 10)
        blob(d, x, 400 + hy, 42, color, t, sq, happy=stopped)
        xs = [x - 120 + j * 60 for j in range(2 + added)]
        line(d, [(xs[0], 560), (xs[-1], 560)], mix(color, INK, 0.2), 8)
        for j, nx in enumerate(xs):
            r = 14 * (ease_out_back((t - OFFLINE_ADDS[j - 2]) / 0.3) if j >= 2 else 1)
            ellipse(d, nx, 560, max(r, 1), max(r, 1), WHITE, INK, 4)
    text_pop(d, 640, 665, "サーバーが止まっても、手元で作業を続けられる", 34, t - 1.2, stagger=0.02)


# ---------------------------------------------------------------- 7. もし素材の配布が中央まかせだと

CENTRAL_STAMP_AT = 2.0


def scene_central(img, d, t):
    stamped = t > CENTRAL_STAMP_AT
    if stamped:
        text_pop(d, 640, 55, "ある日とつぜん「公開停止」！", 42, t - CENTRAL_STAMP_AT, stagger=0.02)
    else:
        text_pop(d, 640, 55, "もし素材の配布が中央まかせだと…", 42, t - 0.1)
    tower(d, 640, 270, 1.0, t)
    for i, color in enumerate(CHAR_COLORS):
        x = 240 + i * 200
        if not stamped:
            dashed(d, (640, 440), (x, 480), (190, 180, 195), 3, 16)
            star(d, x, 505, 22, rot=t * 1.5 + i)
        else:
            k = clamp((t - CENTRAL_STAMP_AT - 0.2) / 0.8)
            if k < 0.95:
                star(d, x, 505 + k * 50, 22 * (1 - k), fill=(190, 190, 195))
        hy, sq = hop(t + i * 0.1, 0.6, 0 if stamped else 6)
        blob(d, x, 615 + hy, 42, color, t, sq, sad=t > CENTRAL_STAMP_AT + 0.3, look=(640 - x) / 900, ground=660)
    if stamped:
        stamp(d, 930, 200, "公開停止", clamp((t - CENTRAL_STAMP_AT) / 0.3))
    since = t - CENTRAL_STAMP_AT
    if 0 < since < 0.35:
        return {"shake": 8 * (1 - since / 0.35)}
    return None


# ---------------------------------------------------------------- 8. P2P

P2P_HOP_LEN = 0.9
P2P_HOPS = [0, 2, 4, 1, 3]
P2P_ARRIVALS = [(k + 1) * P2P_HOP_LEN for k in range(len(P2P_HOPS) - 1)]


def pc_nodes():
    return [(640 + math.cos(-math.pi / 2 + i * 2 * math.pi / 5) * 250,
             400 + math.sin(-math.pi / 2 + i * 2 * math.pi / 5) * 210) for i in range(5)]


def scene_p2p(img, d, t):
    text_pop(d, 640, 55, "素材は、みんなで手渡し", 44, t - 0.1)
    nodes = pc_nodes()
    tw = (1150, 190)
    fade = clamp(t / 3.0)
    if fade < 1:
        for n in nodes:
            dashed(d, (tw[0], tw[1] + 60), n, mix((170, 170, 185), BG, fade), 2, 20)
    tower(d, tw[0], tw[1], 0.45, t, sulk=t > 2.5, label=False)
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            dashed(d, a, b, (200, 190, 200))
    text_center(d, 640, 410, "ピアどうしで直接", 28, (150, 130, 150))

    idx = int(t // P2P_HOP_LEN)
    has_copy = set(P2P_HOPS[:min(idx + 1, len(P2P_HOPS))])
    for i, (x, y) in enumerate(nodes):
        pc(d, x, y)
        got = i in has_copy
        hy, sq = hop(t + i * 0.13, 0.5, 16 if got else 6)
        blob(d, x, y - 30 + hy, 40, CHAR_COLORS[i], t, sq, happy=got, look=(640 - x) / 500)
        if got:
            star(d, x + 40, y - 70, 16, rot=t * 2 + i)
    for k, at in enumerate(P2P_ARRIVALS):
        x, y = nodes[P2P_HOPS[k + 1]]
        burst(d, x, y - 40, t - at, 0.5, count=8, reach=70)
    if idx < len(P2P_HOPS) - 1:
        a, b = nodes[P2P_HOPS[idx]], nodes[P2P_HOPS[idx + 1]]

        def pos(k):
            return lerp(a[0], b[0], k), lerp(a[1], b[1], k) - 40 - math.sin(k * math.pi) * 120
        star_with_trail(d, pos, (t % P2P_HOP_LEN) / P2P_HOP_LEN, 28, t * 5)
    text_pop(d, 640, 690, "中央がいなくても、ちゃんと届く", 30, t - 2.5)


# ---------------------------------------------------------------- 9. フィナーレ

CONFETTI = [(random.Random(i).uniform(0, W), random.Random(i + 99).uniform(-H, 0),
             random.Random(i + 7).uniform(60, 160), random.Random(i + 3).choice(CHAR_COLORS),
             random.Random(i + 11).uniform(0, math.tau))
            for i in range(110)]
FINALE_WAVE_END = 1.6  # ここまでは順番に跳ねる「ウェーブ」、以降はわちゃわちゃ


def scene_finale(img, d, t):
    for x0, y0, speed, color, rot0 in CONFETTI:
        y = (y0 + t * speed * 2.2) % (H + 40) - 20
        x = x0 + math.sin(t * 3 + x0) * 20
        a = rot0 + t * speed * 0.05
        pts = [(x + math.cos(a + k) * 7 * (1 if k in (0, math.pi) else 0.5), y + math.sin(a + k) * 7)
               for k in (0, math.pi / 2, math.pi, 3 * math.pi / 2)]
        d.polygon([(s(px), s(py)) for px, py in pts], fill=color)
    logo(d, 640, 170, 120, t - 0.1)
    text_pop(d, 640, 290, "描く。分岐する。", 44, t - 0.8)
    text_pop(d, 640, 350, "素材と拡張機能は、誰にも消されない。", 36, t - 1.4, stagger=0.02)
    rng = random.Random(5)
    for i, color in enumerate(CHAR_COLORS):
        period = rng.uniform(0.35, 0.55)
        phase = rng.uniform(0, 1)
        height = rng.uniform(40, 80)
        x = 240 + i * 200
        if t < FINALE_WAVE_END:
            wave_t = t - i * 0.12
            hy, sq = hop(max(wave_t, 0), 0.5, 60) if wave_t > 0 else (0.0, 0.0)
        else:
            hy, sq = hop(t + phase, period, height)
            x += math.sin(t * 4 + i) * 25
        blob(d, x, 560 + hy, 58, color, t, sq, happy=True, look=math.sin(t * 3 + i), ground=620)


# ---------------------------------------------------------------- フレームの組み立て

SCENE_FUNCS = {
    "title": scene_title,
    "draw": scene_draw,
    "panels": scene_panels,
    "history": scene_history,
    "branch": scene_branch,
    "offline": scene_offline,
    "central": scene_central,
    "p2p": scene_p2p,
    "finale": scene_finale,
}
TRANSITION = 0.3  # 場面の切り替えで、丸い顔が画面をふさぐ時間
COVER_R = 760     # 画面全体をふさぐ半径


def transition_cover(d, name, lt, t):
    """場面の切り替えで、キャラクター色の大きな丸い顔が画面をふさいで、しぼむ。"""
    i = SCENE_INDEX[name]
    length = LENGTH[name]
    if i > 0 and lt < TRANSITION:
        r = COVER_R * (1 - ease_in_out(lt / TRANSITION))
        color = CHAR_COLORS[i % len(CHAR_COLORS)]
    elif i < len(SCENE_PLAN) - 1 and lt > length - TRANSITION:
        r = COVER_R * ease_in_out((lt - (length - TRANSITION)) / TRANSITION)
        color = CHAR_COLORS[(i + 1) % len(CHAR_COLORS)]
    else:
        return
    if r > 2:
        blob(d, 640, 360, r, color, t)


def render_frame(t):
    name, lt = scene_at(t)
    img = background().copy()
    d = ImageDraw.Draw(img)
    effect = SCENE_FUNCS[name](img, d, lt) or {}
    transition_cover(d, name, lt, t)
    img = img.resize((W, H), Image.LANCZOS)
    shake = effect.get("shake", 0)
    if shake:
        img = ImageChops.offset(img, int(math.sin(t * 90) * shake), int(math.cos(t * 70) * shake * 0.6))
    if name == SCENE_PLAN[-1][0]:
        fade = clamp((lt - (LENGTH[name] - 0.6)) / 0.6)
        if fade > 0:
            img = Image.blend(img, Image.new("RGB", (W, H), BG), fade)
    return img
