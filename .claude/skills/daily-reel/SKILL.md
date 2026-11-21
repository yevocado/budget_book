---
name: daily-reel
description: 오늘의 AI 뉴스 릴스를 에이전트 팀(리서치 → 작성 → 훅 → 휴먼톤 → 검수 → 캡션)으로 만들어 scripts/에 대본을 저장하고 푸시한다. "오늘 릴스 만들어줘", "릴스 하나 뽑아줘", "/daily-reel" 같은 요청에 사용.
---
# 매일 AI 뉴스 릴스 제작

`.claude/agents/`의 서브에이전트를 순서대로 불러서 오늘 올릴 대본 하나를 완성한다. 각 단계의 결과를 다음 에이전트에게 그대로 넘긴다.
인자: 주제(없으면 오늘 AI 업계 전체), 기간(기본: 최근 24시간. 월요일이면 주말 포함 72시간).

## 순서
1. **news-researcher**: 기간과 주제를 주고 후보를 받는다. 이미 올린 소식(`scripts/`의 최근 7개 대본)은 빼라고 함께 전한다.
2. **script-writer**: 리서치 결과 전체를 주고 대본 JSON을 받는다. 소식은 2~3개. 센 소식이 하나뿐이면 1개를 깊게 다뤄도 된다.
3. **hook-editor**: 대본 JSON을 주고, 다듬은 전체 JSON을 받는다.
4. **human-tone-editor**: 대본 JSON을 주고, 다듬은 전체 JSON을 받는다.
5. **fact-checker**: 리서치 결과 + 대본 JSON을 준다. FIX면 제안대로 고친 뒤 한 번 더 검수한다 (최대 2회). 2회 뒤에도 FIX면 사용자에게 문제를 보고하고 멈춘다.
6. **caption-writer**: 리서치 출처 + 최종 대본을 주고 캡션을 받아 `caption` 필드에 넣는다.

## 저장
- 번호: `scripts/`와 `scripts/archive/` 안 가장 큰 번호 + 1 (세 자리).
- 파일: `scripts/NNN_ai_daily_YYYYMMDD.json`. `id`는 파일 이름에서 `.json`을 뺀 것.
- 고정 필드: `"style": "R", "brand": "ai.brief.unni", "hook_sub": "M.D (요일)"` (예: "11.21 (토)").
- 형식은 `scripts/archive/005_ai_news_w47_R.json`과 똑같이 맞춘다. 포즈는 point / present / laptop / think / thumbsup / wave 중에서. 저장 후 `python3 -c "import json;json.load(open(경로))"`로 JSON이 깨지지 않았는지 확인한다.
- 검수 기록: `reports/NNN_....md`에 리서치 요약, 팩트체크 판정표, 출처 URL을 남긴다.

## 마무리
- 대본과 기록을 커밋하고 푸시한다. 푸시하면 GitHub Actions(render.yml)가 영상과 캐러셀(`output/<id>_carousel/01.png…`, 1080x1350)을 만들어 `output/`에 올린다.
- 캐러셀만 따로 만들 땐 `node carousel.js <대본> output`.
- 빠른 확인이 필요하면 `python3 reel.py <대본> --no-tts --frames 2,8,14`로 프레임만 먼저 뽑아 본다.
- 사용자에게: 고른 소식, 팩트체크 결과(특히 뺀 내용과 이유), 영상 경로를 짧게 알린다.
