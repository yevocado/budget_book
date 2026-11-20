# 공감 릴스 자동화

대본 JSON 하나 → 음성합성(Edge TTS) + 자막 카드 → 15~25초 세로 릴스(mp4) 자동 생성.

## 구조
- `scripts/*.json` — 릴스 대본 (훅 → 특징 4~5개 → 반전 → "친구한테 보내줘" CTA)
- `make_reel.py` — 렌더러
- `output/` — 결과물 (`.mp4`, 표지 `.jpg`, 캡션 `.txt`)
- `.github/workflows/render.yml` — `scripts/`에 JSON 올리면 자동 렌더링 후 `output/`에 커밋

## 로컬 실행
```bash
pip install -r requirements.txt   # ffmpeg 필요
python make_reel.py scripts/001_kakao_late_reply.json
python make_reel.py scripts/001_kakao_late_reply.json --no-tts   # 무음 미리보기
```

## 새 릴스 만들기
`scripts/001_kakao_late_reply.json`을 복사해서 문구만 바꾸고 push. 테마: `night` / `peach` / `mint`.

## 음성: ElevenLabs (선택)
GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret
- `ELEVENLABS_API_KEY` — ElevenLabs API 키 (필수)
- `ELEVENLABS_VOICE_ID` — 쓸 목소리 ID (선택, 없으면 기본 음성)

키가 없으면 무료 Edge TTS(`ko-KR-SunHiNeural`)로 자동 전환됩니다.
