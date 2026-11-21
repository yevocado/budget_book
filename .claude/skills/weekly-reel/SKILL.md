---
name: weekly-reel
description: 이번 주 AI 뉴스 릴스를 에이전트 팀(리서치 → 작성 → 훅 → 휴먼톤 → 검수 → 캡션)으로 만들어 scripts/에 대본을 저장하고 푸시한다. "이번 주 릴스 만들어줘", "릴스 하나 뽑아줘", "/weekly-reel" 같은 요청에 사용.
---
# 주간 AI 뉴스 릴스 제작

`.claude/agents/`의 서브에이전트를 순서대로 불러서 대본 하나를 완성한다. 각 단계의 결과를 다음 에이전트에게 그대로 넘긴다.
인자: 스타일(R 리소 앵커 / A 속보 / B 신문, 기본 R), 주제(없으면 이번 주 AI 업계 전체), 기간(기본 최근 7일).

## 순서
1. **news-researcher**: 기간과 주제를 주고 후보 5~7개를 받는다.
2. **script-writer**: 리서치 결과 전체와 스타일을 주고 대본 JSON을 받는다.
3. **hook-editor**: 대본 JSON을 주고, 다듬은 전체 JSON을 받는다.
4. **human-tone-editor**: 대본 JSON을 주고, 다듬은 전체 JSON을 받는다.
5. **fact-checker**: 리서치 결과 + 대본 JSON을 준다. FIX면 제안대로 고친 뒤 한 번 더 검수한다 (최대 2회). 2회 뒤에도 FIX면 사용자에게 문제를 보고하고 멈춘다.
6. **caption-writer**: 리서치 출처 + 최종 대본을 주고 캡션을 받아 `caption` 필드에 넣는다.

## 저장
- 번호: `scripts/` 안 가장 큰 번호 + 1 (세 자리).
- 파일: `scripts/NNN_ai_news_YYYYMMDD_{R|A|B}.json`. `id`는 파일 이름에서 `.json`을 뺀 것.
- 스타일별 고정 필드:
  - R (기본): `"style": "R", "hook_sub": "M월 N주차", "plate": "AI 위클리 · 앵커"`. 포즈는 point / present / laptop / think / thumbsup / wave 중에서.
  - A: `"style": "A", "tag": "BREAKING", "channel": "AI 위클리", "hook_sub": "M월 N주차", "theme": "cobalt"`
  - B: `"style": "B", "masthead": "THE AI WEEKLY", "vol": "VOL. NN", "date_label": "YYYY년 M월 N주차", "mast_right": "3분 요약", "stamp": "다음 주<br>또 만나요"`
- 형식은 기존 대본(`scripts/005_ai_news_w47_R.json`, `scripts/003_ai_news_w47_A.json`, `scripts/004_ai_news_w47_B.json`)과 똑같이 맞춘다. 저장 후 `python3 -c "import json;json.load(open(경로))"`로 JSON이 깨지지 않았는지 확인한다.
- 검수 기록: `reports/NNN_....md`에 리서치 요약, 팩트체크 판정표, 출처 URL을 남긴다.

## 마무리
- 대본과 기록을 커밋하고 푸시한다. 푸시하면 GitHub Actions(render.yml)가 영상을 만들어 `output/`에 올린다.
- 빠른 확인이 필요하면 `python3 reel.py <대본> --no-tts --frames 2,6,10`으로 프레임만 먼저 뽑아 본다.
- 사용자에게: 고른 소식 3개, 팩트체크 결과(특히 뺀 내용과 이유), 영상 경로를 짧게 알린다.
