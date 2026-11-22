"""릴스 자동 생성기 v2.

대본 JSON(scripts/*.json) -> 음성합성(ElevenLabs 또는 Edge TTS, 단어별 타이밍 포함)
-> 프레임 단위 애니메이션(Pillow) -> 세로 mp4(FFmpeg)

디자인: 움직이는 격자 배경, 상단 진행바와 태그, 기사 카드 슬라이드인,
단어별 하이라이트 자막, 장면 전환 효과음.

사용법:
    python make_reel.py scripts/002_ai_news_2026w47.json
    python make_reel.py scripts/*.json --out output
    python make_reel.py scripts/002.json --no-tts   # 음성 없이 무음 미리보기
"""

import argparse
import asyncio
import base64
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from tts_text import to_tts  # 발음 사전 + 숫자 읽기 (TTS에 보내는 글자만 바꿈)

W, H = 1080, 1920
FPS = 30
ROOT = Path(__file__).parent
FONT_TITLE = str(ROOT / "fonts" / "BlackHanSans-Regular.ttf")
FONT_BODY = str(ROOT / "fonts" / "Jua-Regular.ttf")
BGM = ROOT / "assets" / "bgm.mp3"  # 있으면 배경음악으로 깔림 (선택)

VOICE = "ko-KR-SunHiNeural"  # 남성: ko-KR-InJoonNeural
RATE = "+12%"
PAD = 0.35  # 장면 끝 여백(초)

THEMES = {
    "news": {"bg": [(10, 10, 16), (48, 10, 22)], "accent": (255, 59, 77), "hi": (255, 222, 60),
             "text": (255, 255, 255), "card": (250, 250, 252), "ink": (18, 18, 24), "sub": (120, 120, 130)},
    "night": {"bg": [(18, 16, 48), (70, 30, 100)], "accent": (255, 214, 64), "hi": (255, 214, 64),
              "text": (255, 255, 255), "card": (255, 255, 255), "ink": (30, 20, 50), "sub": (130, 120, 150)},
    "mint": {"bg": [(10, 40, 40), (20, 110, 95)], "accent": (255, 235, 120), "hi": (255, 235, 120),
             "text": (255, 255, 255), "card": (255, 255, 255), "ink": (15, 40, 40), "sub": (110, 140, 135)},
}

EMOJI_RE = re.compile("[\U00010000-\U0010FFFF☀-➿️→]")
PUNCT_END = re.compile(r"[.,!?…]+$")


def clean(text: str) -> str:
    """폰트에 없는 이모지/기호는 화면에서 제거 (캡션 텍스트 파일에는 그대로 둠)."""
    return EMOJI_RE.sub("", text).replace("·", "|").strip()


# ================================================================ 음성 + 단어 타이밍
EL_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
EL_VOICE = os.environ.get("ELEVENLABS_VOICE_ID", "").strip() or "QPFsEL6IBxlT15xfiD6C"  # 기본: Hana Lee (한국어 여성)
EL_MODEL = os.environ.get("ELEVENLABS_MODEL", "").strip() or "eleven_multilingual_v2"


EL_SETTINGS = {"stability": 0.5, "similarity_boost": 0.8, "style": 0.25, "speed": 1.08}
EL_TAKES = int(os.environ.get("ELEVENLABS_TAKES", "3"))  # 문장 끝이 올라가면 최대 몇 번 다시 생성할지
SENT_GAP = 0.12  # 문장 사이 쉼(초)


def _el_request(text: str, seed: int):
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{EL_VOICE}/with-timestamps?output_format=mp3_44100_128",
        data=json.dumps({"text": text, "model_id": EL_MODEL, "voice_settings": EL_SETTINGS, "seed": seed}).encode(),
        headers={"xi-api-key": EL_KEY, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"ElevenLabs 오류 {e.code}: {e.read().decode(errors='ignore')[:300]}")
    al = data.get("alignment") or data.get("normalized_alignment") or {}
    return base64.b64decode(data["audio_base64"]), al


def _decode(mp3: bytes, sr: int):
    import numpy as np
    out = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", str(sr), "pipe:1"],
                         input=mp3, capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.int16)


def _pitch(x, sr=16000, win=640, hop=160):
    """10ms 간격 기본 주파수(Hz). 무성 구간은 nan."""
    import numpy as np
    x = x.astype(np.float32) / 32768
    out = []
    for i in range(0, len(x) - win, hop):
        s = x[i:i + win] * np.hanning(win)
        if np.sqrt(np.mean(s ** 2)) < 0.01:
            out.append(np.nan)
            continue
        ac = np.correlate(s, s, "full")[win - 1:]
        lo, hi = sr // 450, sr // 120
        k = lo + int(np.argmax(ac[lo:hi]))
        out.append(sr / k if ac[k] > 0.35 * ac[0] else np.nan)
    p = np.array(out)
    med = np.nanmedian(p) if np.any(~np.isnan(p)) else 0
    for i, v in enumerate(p):  # 옥타브 오인식 보정
        if np.isnan(v) or not med:
            continue
        while v < med * 0.65:
            v *= 2
        while v > med * 1.6:
            v /= 2
        p[i] = v
    return p


def ending_rise(mp3: bytes, al: dict) -> float:
    """마지막 음절 음높이가 바로 앞 구간보다 몇 % 높은지 (+면 끝이 올라감)."""
    import numpy as np
    chars, st, en = al.get("characters", []), al.get("character_start_times_seconds", []), al.get("character_end_times_seconds", [])
    j = len(chars) - 1
    while j > 0 and (not chars[j].strip() or chars[j] in ".?!,…"):
        j -= 1
    if j < 3:
        return 0.0
    p = _pitch(_decode(mp3, 16000))
    last = p[int(st[j] * 100):int(en[j] * 100) + 1]
    prev = p[int(st[max(0, j - 6)] * 100):int(st[j] * 100)]
    last, prev = last[~np.isnan(last)], prev[~np.isnan(prev)]
    if len(last) < 2 or len(prev) < 3:
        return 0.0
    return float((np.median(last) / np.median(prev) - 1) * 100)


def _elevenlabs(text: str, path: Path):
    """문장 단위로 생성하고, 끝 억양이 올라간 문장은 다시 생성해서 가장 잘 내려간 버전을 이어 붙인다."""
    import numpy as np
    sents = [x.strip() for x in re.findall(r"[^.?!]+[.?!]?", text) if x.strip()]
    pcm, words, t = [], [], 0.0
    for si, sent in enumerate(sents):
        best = None
        spoken = to_tts(sent)  # 자막은 원문(sent), 소리는 spoken
        for take in range(EL_TAKES):
            mp3, al = _el_request(spoken, seed=1000 + si * 37 + take * 7919)
            rise = 0.0 if sent.endswith("?") else ending_rise(mp3, al)
            if best is None or rise < best[0]:
                best = (rise, mp3, al)
            if rise <= 4:
                break
        rise, mp3, al = best
        print(f"    끝 억양 {rise:+4.0f}% ({take + 1}회 생성) …{sent[-16:]}")
        audio = _decode(mp3, 44100)
        chars, st, en = al.get("characters", []), al.get("character_start_times_seconds", []), al.get("character_end_times_seconds", [])
        joined, i = "".join(chars), 0
        for w, sw in zip(sent.split(), spoken.split()):  # 소리 단어의 시간을 원문 단어에 그대로 대응
            k = joined.find(sw, i)
            if k < 0:
                break
            words.append((w, t + st[k], t + en[k + len(sw) - 1]))
            i = k + len(sw)
        pcm.append(audio)
        t += len(audio) / 44100
        if si < len(sents) - 1:
            pcm.append(np.zeros(int(SENT_GAP * 44100), dtype=np.int16))
            t += SENT_GAP
    import wave
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(np.concatenate(pcm).tobytes())
    return words if len(words) == len(text.split()) else None


async def _edge(text: str, path: Path):
    import edge_tts
    try:
        comm = edge_tts.Communicate(to_tts(text), VOICE, rate=RATE, boundary="WordBoundary")
    except TypeError:
        comm = edge_tts.Communicate(to_tts(text), VOICE, rate=RATE)
    marks = []
    with open(path, "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                marks.append((ch["offset"] / 1e7, (ch["offset"] + ch["duration"]) / 1e7))
    words = text.split()
    if len(marks) == len(words):
        return [(w, s, e) for w, (s, e) in zip(words, marks)]
    if marks:  # 개수가 안 맞으면 말한 구간 안에서 글자 수 비율로 분배
        return estimate_words(text, marks[0][0], marks[-1][1])
    return None


def estimate_words(text, start, end):
    words = text.split()
    weights = [len(w) + 1 for w in words]
    total, t, out = sum(weights), start, []
    for w, wt in zip(words, weights):
        d = (end - start) * wt / total
        out.append((w, t, t + d))
        t += d
    return out


def audio_duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def make_voice(text: str, path: Path, use_tts: bool):
    """음성 파일을 만들고 (길이, [(단어, 시작, 끝)]) 반환."""
    words = None
    if use_tts:
        words = _elevenlabs(text, path) if EL_KEY else asyncio.run(_edge(text, path))
        dur = audio_duration(path)
    else:
        dur = max(1.2, len(text) * 0.1)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                        "-t", f"{dur:.2f}", str(path)], check=True)
    return dur, words or estimate_words(text, 0.05, dur - 0.1)


# ================================================================ 그리기 도우미
@lru_cache(maxsize=256)
def font(path, size):
    return ImageFont.truetype(path, max(8, int(size)))


def ease_out(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def ease_back(t):
    t = min(1.0, max(0.0, t))
    c1 = 1.9
    return 1 + (c1 + 1) * (t - 1) ** 3 + c1 * (t - 1) ** 2


def fit_size(path, text, max_w, start, min_size=40):
    size = start
    while size > min_size:
        f = font(path, size)
        if max(f.getlength(line) for line in text.split("\n")) <= max_w:
            return size
        size -= 4
    return min_size


def text_sprite(text, path, size, fill, stroke=0, stroke_fill=(0, 0, 0), spacing=14, align="center"):
    """텍스트를 투명 이미지로 미리 렌더 (애니메이션 때 크기/투명도만 바꿔서 씀)."""
    f = font(path, size)
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    box = tmp.multiline_textbbox((0, 0), text, font=f, spacing=spacing, align=align, stroke_width=stroke)
    w, h = math.ceil(box[2] - box[0]) + 20, math.ceil(box[3] - box[1]) + 20
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).multiline_text((10 - box[0], 10 - box[1]), text, font=f, fill=fill, spacing=spacing,
                                       align=align, stroke_width=stroke, stroke_fill=stroke_fill)
    return img


def paste_anim(frame, sprite, cx, cy, scale=1.0, alpha=1.0):
    """sprite를 (cx, cy) 중심에 scale/alpha 적용해서 합성."""
    if alpha <= 0.01 or scale <= 0.01:
        return
    sp = sprite
    if abs(scale - 1) > 0.005:
        sp = sprite.resize((max(1, int(sprite.width * scale)), max(1, int(sprite.height * scale))), Image.BILINEAR)
    if alpha < 0.99:
        a = sp.getchannel("A").point(lambda v: int(v * alpha))
        sp = sp.copy()
        sp.putalpha(a)
    frame.alpha_composite(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)))


# ================================================================ 장면 요소
class Background:
    def __init__(self, theme):
        top, bot = theme["bg"]
        base = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(base)
        for y in range(H):
            t = y / H
            d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bot)))
        self.base = base.convert("RGBA")
        # 움직이는 격자
        g = 72
        self.grid_step = g
        self.grid = Image.new("RGBA", (W + g, H + g), (0, 0, 0, 0))
        gd = ImageDraw.Draw(self.grid)
        for x in range(0, W + g, g):
            gd.line([(x, 0), (x, H + g)], fill=(255, 255, 255, 13), width=2)
        for y in range(0, H + g, g):
            gd.line([(0, y), (W + g, y)], fill=(255, 255, 255, 13), width=2)
        # 떠다니는 빛
        self.glow = Image.new("RGBA", (W + 400, H + 400), (0, 0, 0, 0))
        gl = ImageDraw.Draw(self.glow)
        gl.ellipse([W * 0.45, 0, W + 400, 900], fill=(*theme["accent"], 70))
        gl.ellipse([0, H - 500, W * 0.6, H + 400], fill=(*theme["accent"], 40))
        self.glow = self.glow.filter(ImageFilter.GaussianBlur(150))
        # 비네팅
        vig = Image.new("L", (W, H), 0)
        ImageDraw.Draw(vig).ellipse([-W * 0.35, -H * 0.2, W * 1.35, H * 1.2], fill=255)
        vig = vig.filter(ImageFilter.GaussianBlur(220))
        self.vignette = Image.new("RGBA", (W, H), (0, 0, 0, 150))
        self.vignette.putalpha(vig.point(lambda v: int((255 - v) * 0.6)))

    def frame(self, t):
        img = self.base.copy()
        off = int(t * 24) % self.grid_step
        img.alpha_composite(self.grid, (0, 0), (off, off, off + W, off + H))
        sx = int(200 + math.sin(t * 0.5) * 160)
        sy = int(200 + math.cos(t * 0.4) * 160)
        img.alpha_composite(self.glow, (0, 0), (sx, sy, sx + W, sy + H))
        img.alpha_composite(self.vignette)
        return img


def make_card(item, theme):
    """기사 카드: 출처 / 헤드라인 / 핵심 한 줄."""
    cw, padx = 940, 60
    head = clean(item.get("headline") or item["text"])
    hs = fit_size(FONT_TITLE, head, cw - padx * 2, 96, 50)
    head_sp = text_sprite(head, FONT_TITLE, hs, theme["ink"], spacing=20, align="left")
    src = clean(item.get("source", ""))
    fact = clean(item.get("fact", ""))
    src_h = 70 if src else 0
    fact_sp = text_sprite(fact, FONT_BODY, fit_size(FONT_BODY, fact, cw - padx * 2, 50, 30),
                          theme["sub"], align="left") if fact else None
    ch = 60 + src_h + head_sp.height + (40 + 10 + 30 + fact_sp.height if fact_sp else 0) + 50
    m = 50  # 그림자 여백
    card = Image.new("RGBA", (cw + m * 2, ch + m * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([m, m + 18, m + cw, m + ch + 18], 40, fill=(0, 0, 0, 150))
    card.alpha_composite(sh.filter(ImageFilter.GaussianBlur(24)))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([m, m, m + cw, m + ch], 40, fill=theme["card"])
    d.rounded_rectangle([m, m, m + 16, m + ch], 8, fill=theme["accent"])
    y = m + 60
    if src:
        d.ellipse([m + padx, y + 8, m + padx + 26, y + 34], fill=theme["accent"])
        d.text((m + padx + 44, y + 21), src, font=font(FONT_BODY, 40), fill=theme["sub"], anchor="lm")
        y += src_h
    card.alpha_composite(head_sp, (m + padx - 10, y - 10))
    y += head_sp.height
    if fact_sp:
        y += 40
        d.line([(m + padx, y), (m + cw - padx, y)], fill=(*theme["sub"], 90), width=3)
        y += 40
        card.alpha_composite(fact_sp, (m + padx - 10, y - 10))
    return card


def draw_header(frame, s, theme, t, scene_i, n_scenes, scene_p):
    d = ImageDraw.Draw(frame, "RGBA")
    # 스토리 형식 분할 진행바
    x0, x1, y, gap = 60, W - 60, 120, 12
    seg = (x1 - x0 - gap * (n_scenes - 1)) / n_scenes
    for i in range(n_scenes):
        a = x0 + i * (seg + gap)
        d.rounded_rectangle([a, y, a + seg, y + 10], 5, fill=(255, 255, 255, 60))
        fill = 1.0 if i < scene_i else (scene_p if i == scene_i else 0)
        if fill > 0:
            d.rounded_rectangle([a, y, a + seg * fill, y + 10], 5, fill=(255, 255, 255, 235))
    # 태그 + 채널명
    tag = s.get("tag")
    x = 60
    if tag:
        ft = font(FONT_TITLE, 44)
        tw = ft.getlength(tag)
        d.rounded_rectangle([x, 170, x + tw + 78, 240], 14, fill=theme["accent"])
        if int(t * 2.5) % 2 == 0:  # 깜빡이는 LIVE 점
            d.ellipse([x + 22, 194, x + 44, 216], fill=(255, 255, 255))
        d.text((x + 56, 206), tag, font=ft, fill=(255, 255, 255), anchor="lm")
        x += tw + 100
    label = clean(" · ".join(v for v in [s.get("channel", ""), s.get("hook_sub", "")] if v))
    if label:
        d.text((x, 206), label, font=font(FONT_BODY, 44), fill=(255, 255, 255, 210), anchor="lm")


def chunk_words(words, max_chars=10, max_words=3):
    chunks, cur = [], []
    for w in words:
        if cur and (sum(len(x[0]) for x in cur) + len(w[0]) > max_chars or len(cur) >= max_words):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if PUNCT_END.search(w[0]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def draw_caption(frame, chunks, t, theme, cy):
    """단어별 하이라이트 자막: 현재 묶음을 보여주고, 지금 읽는 단어만 노란색."""
    cur = None
    for i, ch in enumerate(chunks):
        nxt = chunks[i + 1][0][1] if i + 1 < len(chunks) else 1e9
        if ch[0][1] - 0.05 <= t < nxt:
            cur = ch
            break
    if cur is None:
        return
    pop = ease_back((t - cur[0][1] + 0.05) / 0.18)
    words = [clean(PUNCT_END.sub("", w[0])) for w in cur]
    size = fit_size(FONT_TITLE, " ".join(words), W - 140, 104, 60) * (0.82 + 0.18 * pop)
    f = font(FONT_TITLE, size)
    space = f.getlength(" ")
    widths = [f.getlength(w) for w in words]
    x = (W - (sum(widths) + space * (len(words) - 1))) / 2
    d = ImageDraw.Draw(frame, "RGBA")
    for (w, st, _), txt, wd in zip(cur, words, widths):
        active = st - 0.03 <= t
        is_now = active and all(t < o[1] - 0.03 for o in cur if o[1] > st)
        col = theme["hi"] if is_now else (255, 255, 255) if active else (255, 255, 255, 150)
        d.text((x, cy), txt, font=f, fill=col, anchor="lm", stroke_width=9, stroke_fill=(0, 0, 0, 230))
        x += wd + space


# ================================================================ 장면 렌더러
class Scene:
    def __init__(self, kind, s, theme, voice, idx=None):
        self.kind, self.s, self.theme, self.voice, self.idx = kind, s, theme, voice, idx
        self.dur = 0.0
        self.chunks = []
        th = theme
        if kind == "hook":
            lines = clean(s["hook"]).split("\n")
            size = min(fit_size(FONT_TITLE, ln, W - 120, 150) for ln in lines)
            self.lines = [text_sprite(ln, FONT_TITLE, size, th["hi"] if i == len(lines) - 1 else th["text"],
                                      stroke=6, stroke_fill=(0, 0, 0, 200)) for i, ln in enumerate(lines)]
        elif kind == "item":
            item = s["items"][idx]
            self.card = make_card(item, th)
            self.num = text_sprite(f"{idx + 1:02d}", FONT_TITLE, 170, th["accent"], stroke=4, stroke_fill=(0, 0, 0))
            self.total = text_sprite(f"/ {len(s['items']):02d}", FONT_TITLE, 60, (255, 255, 255, 170))
        else:
            text = clean(s["cta"])
            size = fit_size(FONT_TITLE, text, W - 140, 124)
            self.cta = text_sprite(text, FONT_TITLE, size, th["text"], stroke=6, stroke_fill=(0, 0, 0, 200), spacing=24)
            bt = s.get("cta_button", "DM 보내기")
            fb = font(FONT_TITLE, 64)
            bw = int(fb.getlength(bt)) + 200
            self.btn = Image.new("RGBA", (bw + 40, 190), (0, 0, 0, 0))
            bd = ImageDraw.Draw(self.btn)
            bd.rounded_rectangle([20, 20, bw + 20, 170], 75, fill=th["accent"])
            # 종이비행기 아이콘
            ix, iy = 80, 95
            bd.polygon([(ix - 24, iy - 4), (ix + 28, iy - 26), (ix + 8, iy + 28), (ix + 2, iy + 4)], fill=(255, 255, 255))
            bd.text((bw / 2 + 50, 95), bt, font=fb, fill=(255, 255, 255), anchor="mm")
            follow = s.get("follow", "")
            self.follow = text_sprite(clean(follow), FONT_BODY, 50, (255, 255, 255, 200)) if follow else None

    def render(self, frame, t):
        th = self.theme
        if self.kind == "hook":
            n = len(self.lines)
            gap = 175
            y0 = 860 - (n - 1) * gap / 2
            for i, sp in enumerate(self.lines):
                p = ease_back((t - i * 0.22) / 0.3)
                paste_anim(frame, sp, W / 2, y0 + i * gap, scale=max(0.01, p) * (1 + 0.015 * t), alpha=min(1, p * 1.5))
            sub = self.s.get("hook_sub")
            if sub:  # 훅 아래 강조 띠
                p = ease_out((t - n * 0.22) / 0.25)
                if p > 0:
                    d = ImageDraw.Draw(frame, "RGBA")
                    y = y0 + (n - 1) * gap + 130
                    half = 300 * p
                    d.rectangle([W / 2 - half, y, W / 2 + half, y + 10], fill=th["accent"])
        elif self.kind == "item":
            p = ease_out(t / 0.4)
            scale = 1 + 0.035 * (t / max(self.dur, 0.1))  # 천천히 확대(켄 번스)
            card_cy = 820
            paste_anim(frame, self.card, W / 2, card_cy + (1 - p) * 160, scale=scale, alpha=p)
            np_ = ease_back((t - 0.1) / 0.3)
            top = card_cy - self.card.height / 2
            paste_anim(frame, self.num, 190, top - 50, scale=max(0.01, np_), alpha=min(1, np_))
            paste_anim(frame, self.total, 345, top - 22, alpha=ease_out((t - 0.25) / 0.3))
            draw_caption(frame, self.chunks, t, th, 1420)
        else:
            p = ease_back(t / 0.35)
            paste_anim(frame, self.cta, W / 2, 800, scale=max(0.01, p), alpha=min(1, p * 1.5))
            bp = ease_back((t - 0.35) / 0.3)
            pulse = 1 + 0.04 * math.sin(max(0, t - 0.7) * 7)
            paste_anim(frame, self.btn, W / 2, 1110, scale=max(0.01, bp) * pulse, alpha=min(1, bp))
            if self.follow:
                paste_anim(frame, self.follow, W / 2, 1290, alpha=ease_out((t - 0.7) / 0.3))


# ================================================================ 합성
def run(cmd):
    subprocess.run(cmd, check=True)


def build(script_path: Path, out_dir: Path, use_tts: bool) -> Path:
    s = json.loads(script_path.read_text(encoding="utf-8"))
    theme = THEMES.get(s.get("theme", "news"), THEMES["news"])
    out_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="reel_"))

    scenes = [Scene("hook", s, theme, s["hook_voice"])]
    scenes += [Scene("item", s, theme, it["voice"], i) for i, it in enumerate(s["items"])]
    scenes += [Scene("cta", s, theme, s["cta_voice"])]

    # 1) 음성 + 타이밍
    wav_list, starts, t = [], [], 0.0
    for i, sc in enumerate(scenes):
        mp3 = work / f"v{i}.mp3"
        dur, words = make_voice(sc.voice, mp3, use_tts)
        sc.dur = dur + PAD
        sc.chunks = chunk_words(words)
        wav = work / f"v{i}.wav"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-af", "apad", "-t", f"{sc.dur:.3f}",
             "-ar", "44100", "-ac", "2", str(wav)])
        wav_list.append(f"file '{wav}'")
        starts.append(t)
        t += sc.dur
        print(f"  장면 {i} ({sc.kind}): {sc.dur:.2f}s  {sc.voice}")
    total = t
    (work / "a.txt").write_text("\n".join(wav_list))
    voice = work / "voice.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(work / "a.txt"), str(voice)])

    # 2) 효과음(장면 전환 휙) + 선택 배경음악 믹스
    whoosh = work / "whoosh.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
         "anoisesrc=d=0.4:c=pink:a=0.6,highpass=f=600,lowpass=f=7000,"
         "afade=t=in:d=0.15,afade=t=out:st=0.15:d=0.25,aformat=channel_layouts=stereo,aresample=44100",
         str(whoosh)])
    inputs, filters, labels = ["-i", str(voice)], [], ["[0:a]"]
    for k, st in enumerate(starts[1:], start=1):
        inputs += ["-i", str(whoosh)]
        ms = max(0, int((st - 0.12) * 1000))
        filters.append(f"[{k}:a]adelay={ms}|{ms},volume=0.35[w{k}]")
        labels.append(f"[w{k}]")
    if BGM.exists():
        k = len(starts)
        inputs += ["-stream_loop", "-1", "-i", str(BGM)]
        filters.append(f"[{k}:a]volume=0.12,atrim=0:{total:.2f}[bgm]")
        labels.append("[bgm]")
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=first[aout]")
    audio = work / "audio.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
         "-map", "[aout]", str(audio)])

    # 3) 프레임 렌더 -> ffmpeg 파이프
    out = out_dir / f"{s['id']}.mp4"
    bg = Background(theme)
    proc = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(audio),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(out),
    ], stdin=subprocess.PIPE)
    n_frames = int(total * FPS)
    cover = None
    for fi in range(n_frames):
        gt = fi / FPS
        si = max(i for i, st in enumerate(starts) if st <= gt + 1e-6)
        sc, lt = scenes[si], gt - starts[si]
        frame = bg.frame(gt)
        draw_header(frame, s, theme, gt, si, len(scenes), min(1, lt / sc.dur))
        sc.render(frame, lt)
        rgb = frame.convert("RGB")
        if si == 0 and cover is None and lt >= 1.2:
            cover = rgb
        proc.stdin.write(rgb.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg 인코딩 실패")

    (out_dir / f"{s['id']}_caption.txt").write_text(s.get("caption", ""), encoding="utf-8")
    if cover:
        cover.save(out_dir / f"{s['id']}_cover.jpg", quality=92)
    shutil.rmtree(work)
    print(f"완료: {out} ({total:.1f}초)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scripts", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "output")
    ap.add_argument("--no-tts", action="store_true", help="음성 없이 무음으로 미리보기")
    args = ap.parse_args()
    print("음성:", "없음(미리보기)" if args.no_tts else f"ElevenLabs ({EL_VOICE})" if EL_KEY else f"Edge TTS ({VOICE})")
    for p in args.scripts:
        print(f"▶ {p}")
        build(p, args.out, use_tts=not args.no_tts)


if __name__ == "__main__":
    sys.exit(main())
