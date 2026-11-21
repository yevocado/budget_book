"""릴스 제작 에이전트 파이프라인 (Claude API).

리서치 -> 작성 -> 훅 편집 -> 휴먼톤 -> 팩트체크(필요시 수정 반복) -> 캡션 -> scripts/*.json 저장

각 에이전트의 역할 프롬프트는 .claude/agents/*.md 본문을 그대로 쓴다.
(같은 파일을 Claude Code에서 서브에이전트로도 쓸 수 있음)

사용법:
    python agents/pipeline.py --style A                      # 지난 7일 뉴스로 자동 제작
    python agents/pipeline.py --style B --days 7 --vol 48
    python agents/pipeline.py --style A --topic "애플 AI 발표"  # 특정 주제
필요: ANTHROPIC_API_KEY 환경변수
"""

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Literal, Optional

import anthropic
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / ".claude" / "agents"
MODEL = "claude-opus-5-5"
BETAS = ["server-side-fallback-2026-07-01"]  # 거절 시 서버가 다른 모델로 자동 재시도
WEB_TOOLS = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 12}]

client = anthropic.Anthropic()

Pose = Literal["point", "tablet", "present", "think", "thumbsup", "wave"]


# ---------------------------------------------------------------- 대본 스키마 (structured outputs)
class Stat(BaseModel):
    value: str
    unit: str
    label: str
    sub: str


class Item(BaseModel):
    teaser: str
    teaser_hidden: str
    toc: str
    category: str
    source: str
    headline: str
    facts: list[str]
    stat: Optional[Stat]
    voice: str
    pose: Pose


class Script(BaseModel):
    kicker: str
    hook: str
    hook_note: str
    hook_voice: str
    hook_pose: Pose
    items: list[Item]
    cta_kicker: str
    cta: str
    cta_voice: str
    cta_button: str
    cta_pose: Pose


class Review(BaseModel):
    verdict: Literal["PASS", "FIX"]
    problems: list[str]
    fixed_script: Optional[Script]


class Caption(BaseModel):
    caption: str




# ---------------------------------------------------------------- 공통 호출
def role(name: str) -> str:
    text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
    return text.split("---", 2)[2].strip()


def _check(resp):
    if resp.stop_reason == "refusal":
        raise SystemExit(f"모델이 요청을 거절했어요: {getattr(resp, 'stop_details', None)}")
    if resp.stop_reason == "max_tokens":
        raise SystemExit("응답이 max_tokens에서 잘렸어요.")


def ask_with_web(agent: str, user: str, effort: str = "high") -> str:
    """웹 검색 서버 도구를 쓰는 에이전트. pause_turn이면 이어서 진행."""
    messages = [{"role": "user", "content": user}]
    texts = []
    for _ in range(6):
        resp = client.beta.messages.create(
            model=MODEL, max_tokens=16000, betas=BETAS, fallbacks="default",
            system=role(agent), tools=WEB_TOOLS, messages=messages,
            output_config={"effort": effort},
        )
        texts += [b.text for b in resp.content if b.type == "text"]
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        _check(resp)
        return "\n".join(texts).strip()
    raise SystemExit(f"{agent}: 검색이 너무 오래 이어져 중단했어요.")


def ask_json(agent: str, user: str, schema, effort: str = "medium"):
    resp = client.beta.messages.parse(
        model=MODEL, max_tokens=16000, betas=BETAS, fallbacks="default",
        system=role(agent), messages=[{"role": "user", "content": user}],
        output_format=schema, output_config={"effort": effort},
    )
    _check(resp)
    return resp.parsed_output


def dump(model: BaseModel) -> str:
    return json.dumps(model.model_dump(), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- 파이프라인
def run(style: str, days: int, topic: Optional[str], vol: Optional[int], out_dir: Path) -> Path:
    today = dt.date.today()
    since = today - dt.timedelta(days=days)
    week = (today.day - 1) // 7 + 1
    log = []

    print("1/6 리서치 에이전트: 뉴스 찾는 중...")
    ask = f"기간: {since} ~ {today}." + (f" 주제: {topic}." if topic else " 이번 주 AI·IT 업계 전체에서 찾아줘.")
    research = ask_with_web("news-researcher", ask)
    log.append(("리서치", research))

    print("2/6 작성 에이전트: 대본 쓰는 중...")
    script = ask_json("script-writer",
                      f"디자인 스타일: {style}\n\n리서치 결과:\n{research}\n\n소식 3개를 골라 대본을 써줘.", Script, "high")

    print("3/6 훅 에디터: 첫 3초와 공유 문구 다듬는 중...")
    script = ask_json("hook-editor", f"이 대본의 훅·미리보기·CTA를 다듬어서 전체 대본을 돌려줘.\n\n{dump(script)}", Script)

    print("4/6 휴먼톤 에디터: 말투 자연스럽게 고치는 중...")
    script = ask_json("human-tone-editor", f"이 대본의 말투를 다듬어서 전체 대본을 돌려줘.\n\n{dump(script)}", Script)

    for attempt in range(1, 3):
        print(f"5/6 검수 에이전트: 팩트체크 중 ({attempt}회차)...")
        report = ask_with_web("fact-checker",
                              f"리서치 결과:\n{research}\n\n검수할 대본:\n{dump(script)}")
        log.append((f"팩트체크 {attempt}회차", report))
        review = ask_json("fact-checker",
                          f"아래 검수 보고서를 판정으로 정리해. FIX면 문제를 모두 고친 전체 대본을 fixed_script에 넣어.\n\n"
                          f"보고서:\n{report}\n\n원래 대본:\n{dump(script)}", Review)
        if review.verdict == "PASS":
            break
        print("   수정 필요:", *review.problems, sep="\n   - ")
        if review.fixed_script:
            script = review.fixed_script
    else:
        print("⚠️ 2회 검수 후에도 문제가 남았어요. 보고서를 꼭 직접 확인하세요.")

    print("6/6 캡션 에이전트: 캡션 쓰는 중...")
    cap = ask_json("caption-writer", f"리서치 출처:\n{research}\n\n대본:\n{dump(script)}", Caption)

    # 저장
    nums = [int(m.group(1)) for p in (ROOT / "scripts").glob("*.json") if (m := re.match(r"(\d+)_", p.name))]
    n = max(nums, default=0) + 1
    sid = f"{n:03d}_ai_news_{today:%Y%m%d}_{style}"
    data = {"id": sid, "style": style, **script.model_dump(), "caption": cap.caption}
    data.update({"tag": "BREAKING", "channel": "AI 위클리", "hook_sub": f"{today.month}월 {week}주차", "theme": "cobalt"} if style == "A" else
                {"masthead": "THE AI WEEKLY", "vol": f"VOL. {vol or n}", "date_label": f"{today.year}년 {today.month}월 {week}주차",
                 "mast_right": "3분 요약", "stamp": "다음 주<br>또 만나요"})
    for it in data["items"]:
        if it.get("stat") is None:
            it.pop("stat", None)
    path = out_dir / f"{sid}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rep = ROOT / "reports" / f"{sid}.md"
    rep.parent.mkdir(exist_ok=True)
    rep.write_text(f"# {sid} 제작 기록\n\n" + "\n\n".join(f"## {t}\n\n{b}" for t, b in log), encoding="utf-8")
    print(f"완료: {path}\n검수 기록: {rep}")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", choices=["A", "B"], default="A")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--topic")
    ap.add_argument("--vol", type=int)
    ap.add_argument("--out", type=Path, default=ROOT / "scripts")
    a = ap.parse_args()
    run(a.style, a.days, a.topic, a.vol, a.out)


if __name__ == "__main__":
    sys.exit(main())
