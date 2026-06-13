#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""scrollmapper KJV.json(1769판) → 공통 JSONL.

books 순서가 표준 66권(1=Genesis ... 66=Revelation)이라 인덱스로 BOOKS 매핑.
book별 장 수를 BOOKS와 대조해 구조 검증.
출력: data/kjv/kjv.jsonl  (FORMAT.md 스키마, source="kjv")
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from books import BOOKS

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.normpath(os.path.join(HERE, "..", "data", "kjv"))
RAW = os.path.join(OUTDIR, "kjv_raw.json")
OUT = os.path.join(OUTDIR, "kjv.jsonl")
META = os.path.join(OUTDIR, "_meta_kjv.json")

G11 = "In the beginning God created the heaven and the earth."


def main():
    d = json.load(open(RAW, encoding="utf-8"))
    bs = d["books"]
    assert len(bs) == 66, f"books={len(bs)}"
    out, chap_mismatch = [], []
    for bi, bk in enumerate(bs):
        bnum, code, name_kr, nchap = BOOKS[bi]
        if len(bk["chapters"]) != nchap:
            chap_mismatch.append({"code": code, "got": len(bk["chapters"]), "expect": nchap})
        for ch in bk["chapters"]:
            cn = int(ch["chapter"])
            for v in ch["verses"]:
                txt = re.sub(r"\s+", " ", v["text"]).strip()
                out.append({"book": bnum, "code": code, "name_kr": name_kr,
                            "chapter": cn, "verse": int(v["verse"]),
                            "text": txt, "source": "kjv"})
    out.sort(key=lambda r: (r["book"], r["chapter"], r["verse"]))
    with open(OUT, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    g = next((r["text"] for r in out
              if r["code"] == "GEN" and r["chapter"] == 1 and r["verse"] == 1), None)
    meta = {
        "source": "kjv",
        "version": d["translation"][:70],
        "books": len({r["book"] for r in out}),
        "chapters": sum(len(b["chapters"]) for b in bs),
        "verses": len(out),
        "chap_mismatch": chap_mismatch,
        "golden": {"GEN1:1_ok": g == G11, "GEN1:1": g},
    }
    json.dump(meta, open(META, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
