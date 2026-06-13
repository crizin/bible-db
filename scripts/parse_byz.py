#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""byztxt(Robinson-Pierpont Byzantine 2018) → 그리스어 절 본문 + 단어별 Strong/형태소.

절 본문 = ccat/no-variants (악센트 폴리토닉, 구두점 포함)
단어별   = strongs/with-parsing (lowercase surface + Strong 번호 + 형태소 코드)
versification은 Byzantine/TR 계열(KJV와 거의 동일).
출력: data/greek/byz.jsonl, byz_words.jsonl
"""
import csv, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from books import BOOKS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
BYZ = os.path.join(ROOT, "data", "sources", "byztxt", "csv-unicode")
STRONGS = os.path.join(BYZ, "strongs", "with-parsing")
CCAT = os.path.join(BYZ, "ccat", "no-variants")
OUTDIR = os.path.join(ROOT, "data", "greek")

# USFM code → byztxt 파일 코드
USFM_TO_BYZ = {
    "MAT": "MAT", "MRK": "MAR", "LUK": "LUK", "JHN": "JOH", "ACT": "ACT", "ROM": "ROM",
    "1CO": "1CO", "2CO": "2CO", "GAL": "GAL", "EPH": "EPH", "PHP": "PHP", "COL": "COL",
    "1TH": "1TH", "2TH": "2TH", "1TI": "1TI", "2TI": "2TI", "TIT": "TIT", "PHM": "PHM",
    "HEB": "HEB", "JAS": "JAM", "1PE": "1PE", "2PE": "2PE", "1JN": "1JO", "2JN": "2JO",
    "3JN": "3JO", "JUD": "JUD", "REV": "REV",
}
WORD_RE = re.compile(r"(\S+)\s+(\d+)\s+\{([^}]+)\}")


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    fv = open(os.path.join(OUTDIR, "byz.jsonl"), "w", encoding="utf-8")
    fw = open(os.path.join(OUTDIR, "byz_words.jsonl"), "w", encoding="utf-8")
    nv = nw = 0
    seen, vcount = set(), {}
    for bnum, code, name, _ in BOOKS:
        byz = USFM_TO_BYZ.get(code)
        if not byz:
            continue
        cf = os.path.join(CCAT, f"{byz}.csv")
        sf = os.path.join(STRONGS, f"{byz}.csv")
        if not (os.path.exists(cf) and os.path.exists(sf)):
            continue
        seen.add(code)
        cv = sv = 0
        with open(cf, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                fv.write(json.dumps({"book": bnum, "code": code, "name_kr": name,
                                     "chapter": int(row["chapter"]), "verse": int(row["verse"]),
                                     "text": row["text"].strip(), "source": "byz"},
                                    ensure_ascii=False) + "\n")
                nv += 1; cv += 1
        with open(sf, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ch, vs = int(row["chapter"]), int(row["verse"])
                sv += 1
                for wi, m in enumerate(WORD_RE.finditer(row["text"]), 1):
                    fw.write(json.dumps({"book": bnum, "code": code, "chapter": ch, "verse": vs,
                                         "w": wi, "surface": m.group(1),
                                         "strong": [int(m.group(2))], "morph": m.group(3)},
                                        ensure_ascii=False) + "\n")
                    nw += 1
        vcount[code] = (cv, sv)
    fv.close(); fw.close()
    # ccat 절수 vs strongs 절수 불일치 = 조인 위험 신호
    mismatch = {k: v for k, v in vcount.items() if v[0] != v[1]}
    meta = {"source": "byz", "books": len(seen), "verses": nv, "words": nw,
            "verse_count_mismatch": mismatch}
    json.dump(meta, open(os.path.join(OUTDIR, "_meta_byz.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
