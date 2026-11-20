"""공감형 릴스 자동 생성기.

대본 JSON(scripts/*.json) -> 음성합성(Edge TTS) -> 장면 이미지(Pillow) -> 세로 mp4(FFmpeg)

사용법:
    python make_reel.py scripts/001_kakao_late_reply.json
    python make_reel.py scripts/*.json --out output
    python make_reel.py scripts/001.json --no-tts   # 음성 없이 미리보기(무음)
"""

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
ROOT = Path(__file__).parent
FONT_TITLE = str(ROOT / "fonts" / "BlackHanSans-Regular.ttf")
FONT_BODY = str(ROOT / "fonts" / "Jua-Regular.ttf")

VOICE = "ko-KR-SunHiNeural"  # 남성: ko-KR-InJoonNeural
RATE = "+12%"                # 숏폼은 살짝 빠르게
PAD = 0.35                   # 장면 사이 여백(초)

THEMES = {
    "night": {"bg": [(24, 20, 56), (82, 38, 110)], "accent": (255, 214, 64), "text": (255, 255, 255), "dim": (150, 140, 190)},
    "peach": {"bg": [(255, 156, 120), (255, 94, 120)], "accent": (255, 255, 255), "text": (40, 20, 30), "dim": (120, 60, 70)},
    "mint": {"bg": [(20, 60, 60), (30, 140, 120)], "accent": (255, 235, 120), "text": (255, 255, 255), "dim": (140, 200, 190)},
}

EMOJI_RE = re.compile("[\U00010000-\U0010FFFF☀-➿️]")


def clean(text: str) -> str:
    """폰트에 없는 이모지는 화면에서 제거 (캡션에는 그대로 둠)."""
    return EMOJI_RE.sub("", text).replace("→", "").strip()


# ---------------------------------------------------------------- 음성
# ELEVENLABS_API_KEY 환경변수가 있으면 ElevenLabs, 없으면 무료 Edge TTS
EL_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
EL_VOICE = os.environ.get("ELEVENLABS_VOICE_ID", "").strip() or "21m00Tcm4TlvDq8ikWAM"
EL_MODEL = os.environ.get("ELEVENLABS_MODEL", "").strip() or "eleven_multilingual_v2"


def _elevenlabs(text: str, path: Path) -> None:
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{EL_VOICE}?output_format=mp3_44100_128",
        data=json.dumps({
            "text": text,
            "model_id": EL_MODEL,
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.3, "speed": 1.08},
        }).encode(),
        headers={"xi-api-key": EL_KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            path.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"ElevenLabs 오류 {e.code}: {e.read().decode(errors='ignore')[:300]}")


async def _edge(text: str, path: Path) -> None:
    import edge_tts
    await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(path))


def _tts(text: str, path: Path) -> None:
    if EL_KEY:
        _elevenlabs(text, path)
    else:
        asyncio.run(_edge(text, path))


def audio_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def make_voice(text: str, path: Path, use_tts: bool) -> float:
    if use_tts:
        _tts(text, path)
    else:  # 무음 미리보기: 글자 수로 길이 추정
        dur = max(1.2, len(text) * 0.11)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "anullsrc=r=24000:cl=mono", "-t", f"{dur:.2f}", str(path)], check=True)
    return audio_duration(path)


# ---------------------------------------------------------------- 그림
def gradient(top, bottom) -> Image.Image:
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


def fit_font(path, text, max_w, start, min_size=40):
    size = start
    while size > min_size:
        f = ImageFont.truetype(path, size)
        widest = max(f.getlength(line) for line in text.split("\n"))
        if widest <= max_w:
            return f
        size -= 4
    return ImageFont.truetype(path, min_size)


def draw_center(d, y, text, font, fill, spacing=18, shadow=True):
    """여러 줄 텍스트를 가운데 정렬. 그린 블록의 아래 y를 반환."""
    box = d.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align="center")
    tw, th = box[2] - box[0], box[3] - box[1]
    x = (W - tw) / 2
    if shadow:
        d.multiline_text((x + 5, y + 6), text, font=font, fill=(0, 0, 0, 110), spacing=spacing, align="center")
    d.multiline_text((x, y), text, font=font, fill=fill, spacing=spacing, align="center")
    return y + th


def base_frame(theme, progress: float) -> Image.Image:
    img = gradient(*theme["bg"]).convert("RGBA")
    # 은은한 원형 빛
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W * 0.4, -250, W + 350, 750], fill=(255, 255, 255, 30))
    gd.ellipse([-300, H - 700, W * 0.55, H + 200], fill=(255, 255, 255, 25))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(120)))
    # 하단 진행바 (끝까지 보게 만드는 장치)
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([80, H - 150, W - 80, H - 136], 7, fill=(255, 255, 255, 50))
    d.rounded_rectangle([80, H - 150, 80 + (W - 160) * progress, H - 136], 7, fill=theme["accent"])
    return img


def hook_frame(s, theme) -> Image.Image:
    img = base_frame(theme, 0.03)
    d = ImageDraw.Draw(img, "RGBA")
    title = clean(s["hook"])
    f = fit_font(FONT_TITLE, title, W - 120, 150)
    bottom = draw_center(d, 700, title, f, theme["text"])
    sub = clean(s.get("hook_sub", ""))
    if sub:
        fs = ImageFont.truetype(FONT_BODY, 78)
        tw = fs.getlength(sub) + 80
        y = bottom + 70
        d.rounded_rectangle([(W - tw) / 2, y, (W + tw) / 2, y + 120], 60, fill=theme["accent"])
        d.text((W / 2, y + 60), sub, font=fs, fill=theme["bg"][0], anchor="mm")
    return img


def item_frame(s, theme, idx) -> Image.Image:
    items = s["items"]
    img = base_frame(theme, (idx + 1) / (len(items) + 1))
    d = ImageDraw.Draw(img, "RGBA")
    # 상단 고정 제목
    ft = fit_font(FONT_TITLE, clean(s["hook"]), W - 160, 76)
    d.text((W / 2, 230), clean(s["hook"]), font=ft, fill=theme["text"], anchor="mm")
    # 번호 뱃지
    last = idx == len(items) - 1
    label = "반전" if last and len(items) >= 4 else str(idx + 1)
    fb = ImageFont.truetype(FONT_TITLE, 110 if label.isdigit() else 70)
    d.ellipse([W / 2 - 110, 560, W / 2 + 110, 780], fill=theme["accent"])
    d.text((W / 2, 672), label, font=fb, fill=theme["bg"][0], anchor="mm")
    # 본문
    body = clean(items[idx]["text"])
    fbody = fit_font(FONT_BODY, body, W - 140, 104)
    draw_center(d, 880, body, fbody, theme["text"], spacing=30)
    # 남은 개수 점
    n = len(items)
    for i in range(n):
        cx = W / 2 + (i - (n - 1) / 2) * 50
        col = theme["accent"] if i <= idx else (255, 255, 255, 70)
        d.ellipse([cx - 11, 1560, cx + 11, 1582], fill=col)
    return img


def cta_frame(s, theme) -> Image.Image:
    img = base_frame(theme, 1.0)
    d = ImageDraw.Draw(img, "RGBA")
    text = clean(s["cta"])
    f = fit_font(FONT_TITLE, text, W - 160, 120)
    bottom = draw_center(d, 760, text, f, theme["text"], spacing=28)
    # 공유(종이비행기) 버튼 느낌
    y = bottom + 90
    d.rounded_rectangle([W / 2 - 230, y, W / 2 + 230, y + 130], 65, fill=theme["accent"])
    fb = ImageFont.truetype(FONT_TITLE, 64)
    d.text((W / 2, y + 66), "DM 보내기", font=fb, fill=theme["bg"][0], anchor="mm")
    return img


# ---------------------------------------------------------------- 합성
def build(script_path: Path, out_dir: Path, use_tts: bool) -> Path:
    s = json.loads(script_path.read_text(encoding="utf-8"))
    theme = THEMES.get(s.get("theme", "night"), THEMES["night"])
    out_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="reel_"))

    scenes = [(hook_frame(s, theme), s["hook_voice"])]
    scenes += [(item_frame(s, theme, i), it["voice"]) for i, it in enumerate(s["items"])]
    scenes += [(cta_frame(s, theme), s["cta_voice"])]

    concat_v, concat_a = [], []
    for i, (img, voice) in enumerate(scenes):
        png, mp3 = work / f"s{i}.png", work / f"s{i}.mp3"
        img.convert("RGB").save(png)
        dur = make_voice(voice, mp3, use_tts) + PAD
        concat_v.append(f"file '{png}'\nduration {dur:.3f}")
        concat_a.append((mp3, dur))
        print(f"  장면 {i}: {dur:.2f}s  {voice}")
    concat_v.append(f"file '{work / f's{len(scenes) - 1}.png'}'")  # concat 마지막 프레임 규칙
    (work / "v.txt").write_text("\n".join(concat_v))

    # 장면별 음성 + 여백을 이어붙임
    wavs = []
    for i, (mp3, dur) in enumerate(concat_a):
        wav = work / f"a{i}.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-af", "apad",
                        "-t", f"{dur:.3f}", "-ar", "44100", "-ac", "2", str(wav)], check=True)
        wavs.append(f"file '{wav}'")
    (work / "a.txt").write_text("\n".join(wavs))

    out = out_dir / f"{s['id']}.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(work / "v.txt"),
        "-f", "concat", "-safe", "0", "-i", str(work / "a.txt"),
        "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(out),
    ], check=True)
    (out_dir / f"{s['id']}_caption.txt").write_text(s.get("caption", ""), encoding="utf-8")
    scenes[0][0].convert("RGB").save(out_dir / f"{s['id']}_cover.jpg", quality=92)
    shutil.rmtree(work)
    print(f"완료: {out} ({audio_duration(out):.1f}초)")
    return out


def main():
    print("음성:", f"ElevenLabs ({EL_VOICE})" if EL_KEY else f"Edge TTS ({VOICE})")
    ap = argparse.ArgumentParser()
    ap.add_argument("scripts", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "output")
    ap.add_argument("--no-tts", action="store_true", help="음성 없이 무음으로 미리보기")
    args = ap.parse_args()
    for p in args.scripts:
        print(f"▶ {p}")
        build(p, args.out, use_tts=not args.no_tts)


if __name__ == "__main__":
    sys.exit(main())
