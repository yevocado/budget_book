"""음성합성용 텍스트 다듬기: 발음 사전 + 숫자 읽기.

- 화면 자막은 원문 그대로 두고, TTS에 보내는 글자만 바꾼다.
- 단어 수를 바꾸지 않는다(단어별 자막 타이밍을 원문 단어에 그대로 대응시키기 위해).

숫자 규칙
- 양(수량·금액·연도·퍼센트): 한자어로 읽는다. 6,795건 -> 육천칠백구십오건, 2026년 -> 이천이십육년, 83달러 -> 팔십삼달러
- 우리말 단위(개·명·곳·가지·번·시·살 등) 앞 1~99: 고유어로 읽는다. 3개 -> 세개, 20명 -> 스무명
- 소수: 정수부는 양으로, 소수점 아래는 하나씩. 5.1% -> 오점일퍼센트, 87.26 -> 팔십칠점이육
- 하나씩 읽는 숫자: 하이픈·점으로 이어진 코드나 번호(010-1234-5678, 1.2.3), 단위 없이 5자리 이상 이어진 번호. 0101 처럼 0으로 시작하는 번호.
- 영문자와 붙은 숫자(iOS27, K2.6)는 건드리지 않는다. 단 발음 사전에 있는 모델명(GPT-6.2)은 "지피티육점이"처럼 읽는다.
"""
import json
import re
from pathlib import Path

DIG = "영일이삼사오육칠팔구"
NATIVE_ONES = ["", "한", "두", "세", "네", "다섯", "여섯", "일곱", "여덟", "아홉"]
NATIVE_TENS = ["", "열", "스물", "서른", "마흔", "쉰", "예순", "일흔", "여든", "아흔"]
NATIVE_UNITS = ("개", "명", "곳", "가지", "번", "시", "살", "마리", "잔", "장", "권", "대", "군데", "사람")
PRON = {}
_p = Path(__file__).parent / "assets" / "pronunciation.json"
if _p.exists():
    PRON = {k: v for k, v in json.loads(_p.read_text(encoding="utf-8")).items() if not k.startswith("_")}


def sino(n: int) -> str:
    """한자어 수: 6795 -> 육천칠백구십오, 160000000000 -> 천육백억"""
    if n == 0:
        return "영"
    out, groups, i = "", ["", "만", "억", "조", "경"], 0
    while n > 0:
        n, g = divmod(n, 10000)
        if g:
            s = ""
            for val, name in ((1000, "천"), (100, "백"), (10, "십"), (1, "")):
                d, g = divmod(g, val)
                if d:
                    s += ("" if d == 1 and name else DIG[d]) + name
            if groups[i] == "만" and s == "일":
                s = ""  # 일만 -> 만
            out = s + groups[i] + out
        i += 1
    return out


def native(n: int) -> str:
    """고유어 수(1~99, 단위 앞 형태): 3 -> 세, 20 -> 스무, 21 -> 스물한"""
    t, o = divmod(n, 10)
    tens = NATIVE_TENS[t]
    if t == 2 and o == 0:
        tens = "스무"
    return tens + NATIVE_ONES[o]


def one_by_one(s: str) -> str:
    return "".join(DIG[int(c)] if c.isdigit() else ("다시" if c == "-" else "점" if c == "." else c) for c in s)


NUM = re.compile(r"(?<![A-Za-z0-9.])([$€]?)(\d[\d,]*(?:\.\d+)?)([만억조천]*)(%?)(?![\d.]*[A-Za-z])")


def _number(m: re.Match, word: str) -> str:
    cur, num, big, pct = m.group(1), m.group(2), m.group(3), m.group(4)
    after = word[m.end():]
    raw = num.replace(",", "")
    if "." in raw:
        a, b = raw.split(".", 1)
        spoken = sino(int(a)) + "점" + one_by_one(b)
    elif (raw.startswith("0") and len(raw) > 1) or (len(raw) >= 5 and "," not in num and not after):
        spoken = one_by_one(raw)  # 번호·코드
    elif not big and (any(after.startswith(u) for u in NATIVE_UNITS) or (after.startswith("달") and not after.startswith("달러"))) and 1 <= int(raw) <= 99:
        spoken = native(int(raw))
    elif after.startswith("월") and raw in ("6", "10"):
        spoken = "유" if raw == "6" else "시"  # 유월, 시월
    else:
        spoken = sino(int(raw))
    spoken += big
    if pct:
        spoken += "퍼센트"
    if cur == "$":
        spoken += "달러"
    elif cur == "€":
        spoken += "유로"
    return spoken


def tts_word(word: str) -> str:
    m = re.match(r"^(.*?)([A-Za-z]+)-(\d+(?:\.\d+)?)(.*)$", word)
    if m and m.group(2) in PRON:  # GPT-6.2 -> 지피티 육점이 (발음 사전에 있는 모델명만)
        pre, name, ver, post = m.groups()
        a, _, b = ver.partition(".")
        spoken = sino(int(a)) + ("점" + "".join(DIG[int(c)] for c in b) if b else "")
        return pre + PRON[name] + spoken + post
    if re.search(r"[A-Za-z]-?\d", word):  # iOS27, K2.6 같은 이름은 그대로
        return word
    for k, v in sorted(PRON.items(), key=lambda kv: -len(kv[0])):
        word = word.replace(k, v)
    if re.search(r"\d[\d,.]*-\d", word):  # 전화번호·코드
        return re.sub(r"[\d-]+", lambda m: one_by_one(m.group()), word)
    word = re.sub(r"(?<![\d])-(?=\d)", "마이너스", word)  # -7% -> 마이너스칠퍼센트
    return NUM.sub(lambda m: _number(m, word), word)


def to_tts(text: str) -> str:
    """단어 수를 유지하면서 TTS용 문장으로 바꾼다."""
    return " ".join(tts_word(w) for w in text.split(" "))


if __name__ == "__main__":
    for s in ["AI 쇼핑 답변 6,795건 중 9%에 위험 사이트.", "수능 AI 커닝 논란.", "공모가는 주당 83달러, 장중 $87.26까지.",
              "2026년 9월 12일 취임 후 436일.", "소식 3개, 출처 2곳, 20명.", "약 1조6천억원을 순매수.", "삼성전자 -7.01%",
              "문의 010-1234-5678", "iOS 27과 Signal 8.37 이상", "GPT-5.2 출시", "4천억원 넘게", "167년 된 난제", "1859년 제기"]:
        print(s, "->", to_tts(s))
