#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""STEPBible TAGNT → 그리스어 단어별 판본비교 레이어 (byztxt 본문 위에 얹는 보조).

데이터 행(단어): [0] ref#순번=그룹 | [1] 그리스어 (음역) | [2] 문맥글로스
                 | [3] dStrong=형태소 | [4] lemma=의미 | [5] 출현 판본들 | [7] 영어글로스
절 헤더(`# Mat.1.1ⵯ…`)·설명행은 ref#순번 패턴이 아니라 자동 스킵.
라이선스 CC BY 4.0 (출처 표기: github.com/STEPBible). 출력: data/greek/tagnt_words.jsonl
"""
import json, os, re, sys, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from books import NUM_BY_CODE

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SRC = os.path.join(ROOT, "data", "sources", "stepbible")
OUTDIR = os.path.join(ROOT, "data", "greek")

# TAGNT book 코드(3글자 Title) → USFM
TAGNT_TO_USFM = {
    "Mat": "MAT", "Mrk": "MRK", "Luk": "LUK", "Jhn": "JHN", "Act": "ACT", "Rom": "ROM",
    "1Co": "1CO", "2Co": "2CO", "Gal": "GAL", "Eph": "EPH", "Php": "PHP", "Col": "COL",
    "1Th": "1TH", "2Th": "2TH", "1Ti": "1TI", "2Ti": "2TI", "Tit": "TIT", "Phm": "PHM",
    "Heb": "HEB", "Jas": "JAS", "1Pe": "1PE", "2Pe": "2PE", "1Jn": "1JN", "2Jn": "2JN",
    "3Jn": "3JN", "Jud": "JUD", "Rev": "REV",
}
ROW = re.compile(r"^([A-Za-z0-9]+)\.(\d+)\.(\d+)#(\d+)")
GREEK_TRANSLIT = re.compile(r"(.*?)\s*\(([^)]*)\)")


def cell(cols, i):
    return cols[i].strip() if len(cols) > i else ""


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    fw = open(os.path.join(OUTDIR, "tagnt_words.jsonl"), "w", encoding="utf-8")
    nw, skipped, seen = 0, set(), set()
    for path in sorted(glob.glob(os.path.join(SRC, "TAGNT_*.txt"))):
        for line in open(path, encoding="utf-8"):
            cols = line.rstrip("\n").split("\t")
            m = ROW.match(cols[0]) if cols else None
            if not m:
                continue
            bt, ch, vs, wn = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
            code = TAGNT_TO_USFM.get(bt)
            if not code:
                skipped.add(bt); continue
            seen.add(code)
            greek = cell(cols, 1)
            gm = GREEK_TRANSLIT.match(greek)
            surface = gm.group(1).strip() if gm else greek
            translit = gm.group(2).strip() if gm else ""
            ds_morph = cell(cols, 3)
            dstrong, _, morph = ds_morph.partition("=")
            fw.write(json.dumps({
                "book": NUM_BY_CODE[code], "code": code, "chapter": ch, "verse": vs, "w": wn,
                "surface": surface, "translit": translit,
                "dstrong": dstrong.strip(), "morph": morph.strip(),
                "lemma": cell(cols, 4), "context_gloss": cell(cols, 2),
                "editions": cell(cols, 5), "gloss": cell(cols, 7),
            }, ensure_ascii=False) + "\n")
            nw += 1
    fw.close()
    meta = {"source": "tagnt", "books": len(seen), "words": nw,
            "skipped_codes": sorted(skipped)}
    json.dump(meta, open(os.path.join(OUTDIR, "_meta_tagnt.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
