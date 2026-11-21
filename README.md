# AI 위클리 릴스 자동화

뉴스 리서치부터 대본, 검수, 영상까지 에이전트와 렌더러가 자동으로 만들어요.

## 흐름
```
[에이전트 팀]  .claude/agents/*.md  (Claude Code 서브에이전트, API 키 불필요)
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
Claude Code에서 "이번 주 릴스 만들어줘" 또는 `/weekly-reel`이라고 하면 `.claude/skills/weekly-reel/SKILL.md` 순서대로 에이전트들이 돌아가요.

## 자동 실행
- `.github/workflows/render.yml`: `scripts/`에 대본이 푸시되면 그 영상을 렌더링해서 `output/`에 커밋.

## 필요한 시크릿 (Settings → Secrets and variables → Actions)
| 이름 | 용도 |
|---|---|
| `ELEVENLABS_API_KEY` | 고품질 음성 (없으면 무료 Edge TTS) |
| `ELEVENLABS_VOICE_ID` | ElevenLabs 목소리 (없으면 Hana Lee) |

## 디자인
- `"style": "A"` 속보 스타일. `"theme"`: `cobalt`(기본) / `ink` / `tomato` / `forest`
- `"style": "B"` 신문 스타일
- 제목의 `[대괄호]` = 형광펜, `"pose"` = 캐릭터 포즈 (point, tablet, present, think, thumbsup, wave)
- 배경음악: `assets/bgm.mp3`를 넣으면 자동으로 깔림

## 로컬 실행
```bash
pip install -r requirements.txt && npm install playwright && npx playwright install chromium
python reel.py scripts/003_ai_news_w47_A.json  # 영상
python reel.py scripts/003_ai_news_w47_A.json --no-tts --frames 1,5,9   # 프레임 미리보기
```

⚠️ 업로드 전 `reports/`의 검수 기록을 꼭 한 번 확인하세요. 뉴스는 틀리면 계정 신뢰가 끝나요.
