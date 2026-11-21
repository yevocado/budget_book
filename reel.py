"""HTML 템플릿 기반 릴스 생성기 (스타일 A: 다크 속보 / B: 신문).

대본 JSON -> 음성합성 + 단어 타이밍 -> templates/reel.html 애니메이션을 프레임 단위 캡처(render.js)
-> 효과음(휙/사삭/팝/쿵/틱) 자동 믹스 -> mp4

사용법:
    python reel.py scripts/003_ai_news_w47_A.json
    python reel.py scripts/*_A.json scripts/*_B.json --out output
    python reel.py scripts/003.json --no-tts                 # 무음 미리보기
    python reel.py scripts/003.json --no-tts --frames 1,5,9  # 특정 시점 PNG만
"""

import argparse
import array
import json
import random
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

from make_reel import EL_KEY, EL_VOICE, PAD, VOICE, make_voice

ROOT = Path(__file__).parent
BGM = ROOT / "assets" / "bgm.mp3"
SR = 44100


def run(cmd):
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------- 효과음 합성 (외부 파일 없이 ffmpeg로 생성)
SFX_DEFS = {
    # 장면 전환 "휙"
    "whoosh": "anoisesrc=d=0.42:c=pink:a=0.9,highpass=f=300,lowpass=f=6000,afade=t=in:d=0.2:curve=exp,afade=t=out:st=0.2:d=0.22",
    # 글자/줄 스치는 "사삭"
    "swish": "anoisesrc=d=0.2:c=white:a=0.55,highpass=f=2800,lowpass=f=11000,afade=t=in:d=0.05,afade=t=out:st=0.05:d=0.15",
    # 칩/말풍선 "뽁"
    "pop": "aevalsrc='0.8*sin(2*PI*(500+900*exp(-t*35))*t)*exp(-t*28)':d=0.14",
    # 숫자/도장 "쿵"
    "thump": "aevalsrc='0.95*sin(2*PI*(55+140*exp(-t*28))*t)*exp(-t*11)':d=0.32",
    # 손글씨 펜 "사각사각"
    "scribble": "anoisesrc=d=0.45:c=brown:a=0.9,highpass=f=1800,lowpass=f=7000,volume='0.4+0.6*abs(sin(2*PI*14*t))':eval=frame,afade=t=in:d=0.04,afade=t=out:st=0.3:d=0.15",
    # 종이 붙는 "착"
    "paper": "anoisesrc=d=0.12:c=pink:a=0.9,highpass=f=900,lowpass=f=5000,afade=t=out:st=0.01:d=0.11",
    # 카운트업/자막 "틱"
    "tick": "aevalsrc='0.55*sin(2*PI*2300*t)*exp(-t*110)':d=0.05",
    # 캐릭터 등장 "뾰잉"
    "boing": "aevalsrc='0.55*sin(2*PI*(260+220*sin(2*PI*7*t)*exp(-t*6))*t)*exp(-t*7)':d=0.4",
}


def load_mono(path: Path) -> array.array:
    with wave.open(str(path)) as w:
        assert w.getframerate() == SR and w.getnchannels() == 1 and w.getsampwidth() == 2
        return array.array("h", w.readframes(w.getnframes()))


def make_sfx_bank(work: Path) -> dict:
    bank = {}
    for name, src in SFX_DEFS.items():
        p = work / f"sfx_{name}.wav"
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", src, "-ar", str(SR), "-ac", "1", "-sample_fmt", "s16", str(p)])
        bank[name] = load_mono(p)
    return bank


def mouth_envelope(voice_wav: Path, scenes: list, fps=30) -> list:
    """음성 크기(RMS)로 프레임별 입 벌림 정도(0~1). 무음 미리보기면 단어 타이밍으로 흉내."""
    a = load_mono(voice_wav)
    hop = SR // fps
    rms = []
    for i in range(0, len(a), hop):
        seg = a[i:i + hop]
        rms.append((sum(v * v for v in seg[::4]) / max(1, len(seg[::4]))) ** 0.5 if seg else 0)
    peak = sorted(rms)[int(len(rms) * 0.95)] if rms else 0
    if peak < 50:  # 무음
        n = len(rms)
        env = [0.0] * n
        for sc in scenes:
            for w, ws, we in sc["words"]:
                for f in range(int((sc["start"] + ws) * fps), min(n, int((sc["start"] + we) * fps))):
                    env[f] = 0.55 + 0.45 * abs(__import__("math").sin(f * 1.3))
        return [round(v, 2) for v in env]
    env, prev = [], 0.0
    for r in rms:
        v = min(1.0, max(0.0, (r / peak - 0.08) / 0.8))
        v = prev * 0.35 + v * 0.65  # 살짝 부드럽게
        env.append(round(v, 2))
        prev = v
    return env


def mix_sfx(voice_wav: Path, events: list, bank: dict, out: Path, sfx_gain=0.55):
    base = load_mono(voice_wav)
    mixed = array.array("i", base)  # 32bit 누적
    rnd = random.Random(7)
    for ev in events:
        snd = bank.get(ev["type"])
        if snd is None:
            continue
        start = int(ev["t"] * SR)
        g = ev.get("gain", 1) * sfx_gain * rnd.uniform(0.85, 1.0)
        for i, v in enumerate(snd):
            j = start + i
            if j >= len(mixed):
                break
            mixed[j] += int(v * g)
    peak = max(1, max(abs(v) for v in mixed))
    scale = min(1.0, 32000 / peak)
    outa = array.array("h", (int(v * scale) for v in mixed))
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(outa.tobytes())


# ---------------------------------------------------------------- 메인
def build(script_path: Path, out_dir: Path, use_tts: bool, frames: str | None = None) -> Path:
    s = json.loads(script_path.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="reel_"))

    voices = [("hook", None, s["hook_voice"])]
    voices += [("item", i, it["voice"]) for i, it in enumerate(s["items"])]
    voices += [("cta", None, s["cta_voice"])]

    scenes, wavs, t = [], [], 0.0
    for k, (kind, idx, text) in enumerate(voices):
        mp3 = work / f"v{k}.mp3"
        dur, words = make_voice(text, mp3, use_tts)
        lead = 0.25 if kind != "hook" else 0.35  # 음성 시작 전 애니메이션이 먼저 치고 들어갈 여유
        sdur = lead + dur + PAD + (0.6 if kind == "cta" else 0)
        wav = work / f"v{k}.wav"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-af", f"adelay={int(lead * 1000)},apad",
             "-t", f"{sdur:.3f}", "-ar", str(SR), "-ac", "1", "-sample_fmt", "s16", str(wav)])
        wavs.append(f"file '{wav}'")
        scenes.append({"kind": kind, "idx": idx, "start": round(t, 3), "dur": round(sdur, 3),
                       "words": [[w, round(a + lead, 3), round(b + lead, 3)] for w, a, b in words]})
        print(f"  장면 {k} ({kind}): {sdur:.2f}s  {text}")
        t += sdur
    total = t
    (work / "a.txt").write_text("\n".join(wavs))
    voice = work / "voice.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(work / "a.txt"), str(voice)])

    data = {"script": s, "scenes": scenes, "total": round(total, 3), "mouth": mouth_envelope(voice, scenes)}
    (work / "timeline.json").write_text(json.dumps(data, ensure_ascii=False))

    # 프레임 렌더 (브라우저)
    video = work / "video.mp4"
    sfx_json = work / "sfx.json"
    cmd = ["node", str(ROOT / "render.js"), str(work / "timeline.json"), str(video), str(sfx_json)]
    if frames:
        png_dir = out_dir / f"{s['id']}_frames"
        run(cmd + ["--frames", frames, "--png-dir", str(png_dir)])
        print(f"프레임 저장: {png_dir}")
        shutil.rmtree(work)
        return png_dir
    run(cmd)

    # 효과음 믹스 + 선택 배경음악
    events = json.loads(sfx_json.read_text())
    audio = work / "audio.wav"
    mix_sfx(voice, events, make_sfx_bank(work), audio)
    final_audio = audio
    if BGM.exists():
        final_audio = work / "audio_bgm.wav"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(audio), "-stream_loop", "-1", "-i", str(BGM), "-filter_complex",
             f"[1:a]volume=0.12,atrim=0:{total:.2f}[b];[0:a][b]amix=inputs=2:normalize=0:duration=first[a]", "-map", "[a]", str(final_audio)])

    out = out_dir / f"{s['id']}.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(final_audio), "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-shortest", "-movflags", "+faststart", str(out)])
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1.6", "-i", str(video), "-frames:v", "1", "-q:v", "2",
         str(out_dir / f"{s['id']}_cover.jpg")])
    (out_dir / f"{s['id']}_caption.txt").write_text(s.get("caption", ""), encoding="utf-8")
    shutil.rmtree(work)
    print(f"완료: {out} ({total:.1f}초, 효과음 {len(events)}개)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scripts", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "output")
    ap.add_argument("--no-tts", action="store_true")
    ap.add_argument("--frames", help="이 시점(초)들만 PNG로 저장, 예: 1,4.5,9")
    args = ap.parse_args()
    print("음성:", "없음(미리보기)" if args.no_tts else f"ElevenLabs ({EL_VOICE})" if EL_KEY else f"Edge TTS ({VOICE})")
    for p in args.scripts:
        print(f"▶ {p}")
        build(p, args.out, not args.no_tts, args.frames)


if __name__ == "__main__":
    sys.exit(main())
