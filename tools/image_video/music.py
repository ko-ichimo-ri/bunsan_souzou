"""イメージビデオの音楽と効果音を合成する。

120 BPM・1 小節 2 秒。場面の切り替わりは小節の頭にそろっているので、
場面ごとに曲の展開（イントロ・グルーヴ・静かな場面・短調・転調）を変える。
"""

import random
import wave

import numpy as np

import scenes as sc
from timeline import BAR, DURATION, SCENE_PLAN, START, scene_at

SR = 44100
BEAT = BAR / 4

# 場面ごとの曲の展開
SECTION = {
    "title": "intro",
    "draw": "groove",
    "panels": "groove",
    "history": "groove",
    "branch": "groove",
    "offline": "calm",
    "central": "dark",
    "p2p": "lift",
    "finale": "lift",
}

PROGRESSION = [(60, 64, 67), (55, 59, 62), (57, 60, 64), (53, 57, 60)]  # C G Am F
DARK_PROGRESSION = [(57, 60, 64), (52, 56, 59)]  # Am E
LIFT = 2  # p2p 以降は全音上げて盛り上げる

# メロディ（8 分音符 × 8 = 1 小節。None は休符）。和音の進行 C G Am F に合わせて作曲
MELODY_A = [
    [79, None, 76, 79, 84, None, 83, 81],
    [79, None, 74, None, 79, 81, 83, None],
    [84, None, 81, 79, 76, None, 79, 81],
    [77, 76, 74, 76, 72, None, None, None],
]
MELODY_B = [
    [79, None, 76, 79, 84, None, 86, 88],
    [86, None, 83, None, 79, 81, 83, 86],
    [84, None, 88, 86, 84, None, 81, 79],
    [81, 79, 77, 76, 77, None, 79, None],
]
CALM_MELODY = [72, None, None, 76, None, None, 79, None]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def samples(sec):
    return int(sec * SR)


def adsr(n, attack=0.005, decay=0.1, sustain=0.6, release=0.08):
    t = np.arange(n) / SR
    env = np.where(t < attack, t / max(attack, 1e-6),
                   np.maximum(sustain, 1 - (1 - sustain) * (t - attack) / max(decay, 1e-6)))
    rel = np.clip((n / SR - t) / release, 0, 1)
    return env * rel


def phase(freq, n, vibrato=0.0):
    t = np.arange(n) / SR
    f = freq * (1 + vibrato * np.sin(2 * np.pi * 5.5 * t) * np.clip(t / 0.15, 0, 1))
    return np.cumsum(f) / SR % 1.0


def pulse(freq, n, duty=0.25, vibrato=0.0):
    return np.where(phase(freq, n, vibrato) < duty, 1.0, -1.0)


def tri(freq, n):
    return 4 * np.abs(phase(freq, n) - 0.5) - 1


def sine(freq, n):
    return np.sin(2 * np.pi * phase(freq, n))


def soft_saw(freq, n, harmonics=6):
    """倍音を絞ったやわらかいノコギリ波（パッド用）。"""
    t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * freq * k * t) / k for k in range(1, harmonics + 1)) * 0.6


def noise(n, seed):
    return np.random.default_rng(seed).uniform(-1, 1, n)


class Bus:
    """ステレオの音の通り道。"""

    def __init__(self):
        self.l = np.zeros(samples(DURATION) + SR)
        self.r = np.zeros_like(self.l)

    def add(self, sig, at, gain, pan=0.0):
        i = samples(at)
        if i < 0 or i >= len(self.l):
            return
        j = min(len(self.l), i + len(sig))
        a = (pan + 1) * np.pi / 4
        self.l[i:j] += sig[:j - i] * gain * np.cos(a)
        self.r[i:j] += sig[:j - i] * gain * np.sin(a)


# ---------------------------------------------------------------- 楽器

def kick():
    n = samples(0.25)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(50 + 110 * np.exp(-t * 30)) / SR) * np.exp(-t * 11)
    click = noise(n, 1) * np.exp(-t * 400) * 0.3
    return body + click


def snare(seed):
    n = samples(0.18)
    t = np.arange(n) / SR
    nz = np.diff(noise(n + 1, seed)) * 0.6 * np.exp(-t * 22)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    return nz + tone * 0.6


def hat(seed, open_=False):
    n = samples(0.25 if open_ else 0.04)
    t = np.arange(n) / SR
    return np.diff(noise(n + 1, seed)) * 0.5 * np.exp(-t * (12 if open_ else 110))


def crash(seed=3):
    n = samples(1.6)
    t = np.arange(n) / SR
    return np.diff(noise(n + 1, seed)) * 0.5 * np.exp(-t * 2.5)


def lead_note(note, dur):
    n = samples(dur)
    sig = pulse(hz(note), n, 0.25, vibrato=0.004) * 0.6 + pulse(hz(note) * 1.003, n, 0.5) * 0.4
    return sig * adsr(n, 0.005, 0.12, 0.55, 0.05)


def pluck(note, dur):
    n = samples(dur)
    return pulse(hz(note), n, 0.125) * adsr(n, 0.002, 0.06, 0.0, 0.03)


def bass_note(note, dur):
    n = samples(dur)
    return (tri(hz(note), n) * 0.7 + sine(hz(note), n) * 0.5) * adsr(n, 0.004, 0.1, 0.7, 0.04)


def pad_chord(chord, dur):
    n = samples(dur)
    sig = sum(soft_saw(hz(m), n) + soft_saw(hz(m) * 1.004, n) for m in chord) / len(chord)
    return sig * adsr(n, 0.25, 0.3, 0.8, 0.3)


def bell(note, dur=0.6):
    n = samples(dur)
    t = np.arange(n) / SR
    return (sine(hz(note), n) + 0.4 * sine(hz(note) * 2.76, n) * np.exp(-t * 8)) * np.exp(-t * 4)


# ---------------------------------------------------------------- 効果音

def pop(up=True):
    n = samples(0.12)
    t = np.arange(n) / SR
    f = 400 + 1400 * t / 0.12 if up else 1600 - 1200 * t / 0.12
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 28)


def sweep(f0, f1, dur, decay=5.0):
    n = samples(dur)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(np.linspace(f0, f1, n)) / SR) * np.exp(-t * decay)


def whoosh(dur=0.35, seed=0):
    """場面の切り替わりの「シュッ」。"""
    n = samples(dur)
    t = np.arange(n) / SR
    env = np.sin(np.pi * t / dur) ** 2
    return np.diff(noise(n + 1, seed)) * env * 0.5


def arpeggio_sfx(bus, at, notes, step=0.06, gain=0.12):
    for k, note in enumerate(notes):
        bus.add(bell(note, 0.5), at + k * step, gain, pan=(-0.4 + 0.2 * k))


# ---------------------------------------------------------------- 曲

def chord_for(bar_index, section):
    if section == "dark":
        return DARK_PROGRESSION[bar_index % 2]
    return PROGRESSION[bar_index % 4]


def compose(drums, bass, pad, arp, lead):
    """小節ごとに、場面の展開に合わせて各楽器を並べる。"""
    groove_bar = 0  # グルーヴ以降で数える小節。和音とメロディの進行に使う
    dark_bar = 0
    rng = random.Random(7)
    n_bars = int(DURATION / BAR)
    for b in range(n_bars):
        start = b * BAR
        name, _ = scene_at(start + 0.01)
        section = SECTION[name]
        last_bar = b == n_bars - 1
        up = LIFT if section == "lift" else 0
        if section == "dark":
            chord = chord_for(dark_bar, section)
            dark_bar += 1
        else:
            chord = chord_for(groove_bar, section)
        chord = tuple(m + up for m in chord)

        if last_bar:
            # 締め：頭で和音を鳴らして伸ばす
            pad.add(pad_chord(chord + (chord[0] + 12,), BAR * 1.2), start, 0.5)
            bass.add(bass_note(chord[0] - 24, BAR), start, 0.6)
            drums.add(kick(), start, 0.9)
            drums.add(hat(99, open_=True), start, 0.3)
            for k, m in enumerate(chord + (chord[0] + 12,)):
                lead.add(bell(m + 12, 1.5), start + k * 0.08, 0.14, pan=-0.3 + 0.2 * k)
            continue

        next_section = SECTION[scene_at(start + BAR + 0.01)[0]] if b + 1 < n_bars else None
        if start in (START["p2p"], START["finale"]):
            drums.add(crash(), start, 0.3, pan=-0.2)

        # パッド（全場面）
        pad.add(pad_chord(chord, BAR), start, 0.26 if section == "dark" else 0.32)

        # アルペジオ
        if section in ("intro", "groove", "lift", "calm"):
            tones = [chord[0], chord[1], chord[2], chord[0] + 12]
            step = BEAT / 2 if section != "calm" else BEAT
            for k in range(int(BAR / step)):
                note = tones[k % 4] + 12
                arp.add(pluck(note, step * 0.9), start + k * step, 0.16, pan=0.35 if k % 2 else -0.35)

        # ベース
        if section in ("groove", "lift"):
            pattern = [0, 0, 12, 0, 0, 12, 7, 12]
            for k, iv in enumerate(pattern):
                bass.add(bass_note(chord[0] - 24 + iv, BEAT / 2 * 0.9), start + k * BEAT / 2, 0.42)
        elif section == "dark":
            for k in (0, 2):
                bass.add(bass_note(chord[0] - 24, BEAT * 1.8), start + k * BEAT, 0.36)
        elif section == "intro" and b == 1:
            bass.add(bass_note(chord[0] - 24, BAR), start, 0.35)

        # ドラム
        if section in ("groove", "lift"):
            for k in range(4):
                drums.add(kick(), start + k * BEAT, 0.8 if k in (0, 2) else 0.55)
            for k in (1, 3):
                drums.add(snare(b * 4 + k), start + k * BEAT, 0.45, pan=0.1)
            for k in range(8):
                open_ = k == 7 and b % 2 == 1
                drums.add(hat(b * 8 + k, open_), start + k * BEAT / 2, 0.16 if k % 2 else 0.1, pan=0.3)
        elif section == "dark":
            for k in (0, 2):
                drums.add(kick(), start + k * BEAT, 0.75)
            if next_section == "lift":
                # 転調に向けてスネアを連打して盛り上げる
                for k in range(8):
                    drums.add(snare(b * 16 + k), start + 3 * BEAT + k * BEAT / 8, 0.12 + 0.05 * k)
            else:
                drums.add(snare(b), start + 3 * BEAT, 0.3)
        elif section == "calm":
            for k in range(4):
                drums.add(hat(b * 4 + k), start + k * BEAT + BEAT / 2, 0.1, pan=0.3)
        elif section == "intro" and b == 1:
            drums.add(kick(), start, 0.7)
            for k in range(8):
                drums.add(hat(b * 8 + k), start + k * BEAT / 2, 0.06 + 0.02 * k, pan=0.3)

        # メロディ
        if section in ("groove", "lift"):
            phrase = MELODY_A if (groove_bar // 4) % 2 == 0 else MELODY_B
            notes = phrase[groove_bar % 4]
            for k, note in enumerate(notes):
                if note is None:
                    continue
                length = 1
                while k + length < 8 and notes[k + length] is None and length < 3:
                    length += 1
                dur = BEAT / 2 * length * 0.92
                lead.add(lead_note(note + up, dur), start + k * BEAT / 2, 0.2)
                if section == "lift":
                    lead.add(lead_note(note + up + 12, dur), start + k * BEAT / 2, 0.07, pan=0.3)
        elif section == "calm":
            for k, note in enumerate(CALM_MELODY):
                if note is not None:
                    lead.add(bell(note + 12, 0.9), start + k * BEAT / 2, 0.18, pan=rng.uniform(-0.3, 0.3))

        if section != "dark":
            groove_bar += 1 if section != "intro" else 0


def add_sfx(sfx):
    s0 = START
    # 場面の切り替わり
    for i, (name, _) in enumerate(SCENE_PLAN[1:], start=1):
        sfx.add(whoosh(0.4, i), s0[name] - 0.3, 0.18, pan=0.0)
    # タイトル：着地
    for i, at in enumerate(sc.TITLE_LANDS):
        sfx.add(pop(), at, 0.35, pan=-0.6 + i * 0.3)
    # 描く：消しゴム・素材の着地
    sfx.add(pop(False), s0["draw"] + 4.3, 0.25, pan=0.2)
    sfx.add(pop(), s0["draw"] + sc.DRAW_THROW_AT + sc.DRAW_THROW_DUR, 0.35)
    # 履歴：巻き戻しと差分
    sfx.add(sweep(1400, 350, 0.35), s0["history"] + sc.REVERT_AT - 0.2, 0.18)
    arpeggio_sfx(sfx, s0["history"] + sc.REVERT_AT + 0.1, [84, 88, 91])
    arpeggio_sfx(sfx, s0["history"] + sc.DIFF_AT + 0.2, [88, 93], step=0.1)
    # 統合
    arpeggio_sfx(sfx, s0["branch"] + sc.MERGE_AT, [84, 88, 91, 96, 100])
    # サーバー停止と、手元の履歴更新
    sfx.add(sweep(600, 150, 0.5, 4), s0["offline"] + sc.OFFLINE_STOP, 0.2)
    for i, at in enumerate(sc.OFFLINE_ADDS):
        sfx.add(pop(), s0["offline"] + at, 0.22, pan=-0.4 if i % 2 == 0 else 0.4)
    # 公開停止のハンコと、しょんぼり
    n = samples(0.4)
    t = np.arange(n) / SR
    thud = np.sin(2 * np.pi * 60 * t) * np.exp(-t * 9) + np.diff(noise(n + 1, 5)) * np.exp(-t * 40) * 0.5
    sfx.add(thud, s0["central"] + sc.CENTRAL_STAMP_AT, 0.7)
    for k, note in enumerate([72, 69, 65, 60]):
        sfx.add(bell(note, 0.4), s0["central"] + sc.CENTRAL_STAMP_AT + 0.4 + k * 0.22, 0.12)
    # 素材の受け渡し
    for k, at in enumerate(sc.P2P_ARRIVALS):
        sfx.add(pop(), s0["p2p"] + at, 0.3, pan=-0.5 + 0.33 * k)


def ping_pong_delay(bus, delay=BEAT * 0.75, feedback=0.35, level=0.35):
    """左右に交互に跳ね返るやまびこ。"""
    d = samples(delay)
    src = (bus.l + bus.r) / 2
    gain = level
    for k in range(1, 5):
        echo = np.zeros_like(src)
        echo[d * k:] = src[:-d * k]
        if k % 2:
            bus.l += echo * gain
        else:
            bus.r += echo * gain
        gain *= feedback


def sidechain(kick_times, length):
    """キックに合わせて音量を少し沈めるための係数。"""
    env = np.ones(length)
    n = samples(0.22)
    curve = 1 - 0.45 * np.exp(-np.arange(n) / SR * 14)
    for at in kick_times:
        i = samples(at)
        j = min(length, i + n)
        if 0 <= i < length:
            env[i:j] = np.minimum(env[i:j], curve[:j - i])
    return env


def make_audio(path):
    drums, bass, pad, arp, lead, sfx = (Bus() for _ in range(6))
    compose(drums, bass, pad, arp, lead)
    add_sfx(sfx)
    ping_pong_delay(lead)
    kicks = [b * BAR + k * BEAT for b in range(int(DURATION / BAR))
             for k in range(4) if SECTION[scene_at(b * BAR + 0.01)[0]] in ("groove", "lift")]
    duck = sidechain(kicks, len(pad.l))
    l = drums.l + bass.l + (pad.l + arp.l) * duck + lead.l + sfx.l
    r = drums.r + bass.r + (pad.r + arp.r) * duck + lead.r + sfx.r
    total = samples(DURATION)
    out = np.stack([l[:total], r[:total]], axis=1)
    fade_in, fade_out = samples(0.05), samples(1.2)
    out[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    out[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None]
    out = np.tanh(out / np.max(np.abs(out)) * 1.6) / np.tanh(1.6) * 0.9  # やわらかく音割れを防ぐ
    pcm = (out * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
