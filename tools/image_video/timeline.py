"""場面の時間割。映像と音楽の両方がこれを参照する。"""

FPS = 24
BAR = 2.0  # 1 小節の長さ[秒]（120 BPM・4 拍）。場面の切り替わりを小節の頭にそろえる

SCENE_PLAN = [  # （場面名, 長さ[秒]）
    ("title", 4.0),
    ("draw", 6.0),
    ("panels", 6.0),
    ("each_panel", 4.0),
    ("history", 6.0),
    ("branch", 6.0),
    ("offline", 4.0),
    ("central", 4.0),
    ("p2p", 6.0),
    ("finale", 6.0),
]

START = {}
_t = 0.0
for _name, _length in SCENE_PLAN:
    START[_name] = _t
    _t += _length
DURATION = _t
FRAMES = int(FPS * DURATION)
LENGTH = dict(SCENE_PLAN)
SCENE_INDEX = {name: i for i, (name, _) in enumerate(SCENE_PLAN)}


def scene_at(t):
    """時刻 t の場面名と、場面内の経過時間を返す。"""
    for name, _ in reversed(SCENE_PLAN):
        if t >= START[name]:
            return name, t - START[name]
    return SCENE_PLAN[0][0], t
