#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""openscriptures strongs JS 사전 → 정제 JSON.

`var strongsHebrewDictionary = {...};` 래퍼 안의 순수 JSON 추출.
환각 방지 그라운딩용 사전 본체. H1~H8674(+아람어) / G1~G5624.
출력: data/strongs/strongs_hebrew.json, strongs_greek.json
"""
import json, glob, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SRC = os.path.join(ROOT, "data", "sources", "strongs")
OUTDIR = os.path.join(ROOT, "data", "strongs")


def extract(pattern):
    paths = glob.glob(os.path.join(SRC, pattern), recursive=True)
    if not paths:
        raise FileNotFoundError(pattern)
    t = open(paths[0], encoding="utf-8").read()
    return json.loads(t[t.index("{"):t.rindex("}") + 1]), paths[0]


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    heb, hp = extract("**/strongs-hebrew-dictionary.js")
    grk, gp = extract("**/strongs-greek-dictionary.js")
    json.dump(heb, open(os.path.join(OUTDIR, "strongs_hebrew.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    json.dump(grk, open(os.path.join(OUTDIR, "strongs_greek.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))

    h = heb.get("H8414", {})
    g = grk.get("G2316", {})
    print(f"Hebrew entries: {len(heb)} (기대 ~8674)")
    print(f"  H8414 토후: lemma={h.get('lemma')} xlit={h.get('xlit')}")
    print(f"           def={h.get('strongs_def','')[:60]!r}")
    print(f"Greek entries: {len(grk)} (기대 ~5523)")
    print(f"  G2316 theos: lemma={g.get('lemma')} translit={g.get('translit')}")
    print(f"필드(Heb): {list(h.keys())}")
    print(f"필드(Grk): {list(g.keys())}")
    print(f"소스: {os.path.relpath(hp, ROOT)} / {os.path.relpath(gp, ROOT)}")


if __name__ == "__main__":
    main()
