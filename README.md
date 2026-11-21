# AI 위클리 릴스 자동화

뉴스 리서치부터 대본, 검수, 영상까지 에이전트와 렌더러가 자동으로 만들어요.

## 흐름
```
[에이전트 파이프라인]  agents/pipeline.py  (Claude API)
  1. news-researcher    이번 주 AI 뉴스 후보 찾기 (웹 검색, 출처 2곳 이상)
  2. script-writer      소식 3개 골라 대본 JSON 작성
  3. hook-editor        첫 3초 훅 / 미리보기 / 공유 문구 다듬기
  4. human-tone-editor  AI 티 나는 말투 → 사람 말투
  5. fact-checker       모든 사실 주장 재검증, 문제 있으면 고쳐서 재검수 (최대 2회)
  6. caption-writer     인스타 캡션 + 해시태그 + 출처
        ↓ scripts/NNN_*.json, reports/NNN_*.md (검수 기록)
[렌더러]  reel.py → templates/reel.html → render.js
  음성합성(ElevenLabs/Edge TTS) + 키네틱 타이포 + 캐릭터 립싱크 + 효과음 → output/*.mp4
```
에이전트 역할 프롬프트는 `.claude/agents/*.md`에 있어요. Claude Code에서 서브에이전트로도 바로 쓸 수 있어요.

## 자동 실행
- `.github/workflows/weekly.yml`: 매주 월요일 07:17(한국시간)에 에이전트 → 렌더링 → 커밋. Actions 탭에서 수동 실행(스타일/주제 선택)도 가능.
- `.github/workflows/render.yml`: `scripts/`의 대본을 고쳐서 푸시하면 그 영상만 다시 렌더링.

## 필요한 시크릿 (Settings → Secrets and variables → Actions)
| 이름 | 용도 |
|---|---|
| `ANTHROPIC_API_KEY` | 에이전트 (필수) |
| `ELEVENLABS_API_KEY` | 고품질 음성 (없으면 무료 Edge TTS) |
| `ELEVENLABS_VOICE_ID` | ElevenLabs 목소리 |

## 디자인
- `"style": "A"` 속보 스타일. `"theme"`: `cobalt`(기본) / `ink` / `tomato` / `forest`
- `"style": "B"` 신문 스타일
- 제목의 `[대괄호]` = 형광펜, `"pose"` = 캐릭터 포즈 (point, tablet, present, think, thumbsup, wave)
- 배경음악: `assets/bgm.mp3`를 넣으면 자동으로 깔림

## 로컬 실행
```bash
pip install -r requirements.txt && npm install playwright && npx playwright install chromium
python agents/pipeline.py --style A            # ANTHROPIC_API_KEY 필요
python reel.py scripts/003_ai_news_w47_A.json  # 영상
python reel.py scripts/003_ai_news_w47_A.json --no-tts --frames 1,5,9   # 프레임 미리보기
```

⚠️ 업로드 전 `reports/`의 검수 기록을 꼭 한 번 확인하세요. 뉴스는 틀리면 계정 신뢰가 끝나요.
