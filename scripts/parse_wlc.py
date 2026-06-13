#!/usr/bin/env python3
# /// script
# dependencies = ["lxml"]
# ///
"""morphhb WLC OSIS XML → 히브리어 절 본문 + 단어별 Strong/형태소.

versification은 히브리어(WLC) 원본 보존(KJV 매핑은 별도 단계).
출력:
  data/hebrew/wlc.jsonl        — 절 본문 (source="wlc")
  data/hebrew/wlc_words.jsonl  — 단어별 {surface, lemma, strong[], morph}
"""
import json, os, re, sys, glob
from lxml import etree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from books import BOOKS, OSIS_TO_USFM, NAME_BY_CODE

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
WLC = os.path.join(ROOT, "data", "sources", "morphhb", "wlc")
OUTDIR = os.path.join(ROOT, "data", "hebrew")
NS = {"o": "http://www.bibletechnologies.net/2003/OSIS/namespace"}


def strongs(lemma):
    """lemma의 숫자 토큰 = Strong 번호(들). 접두 형태소(b,c,d…)·동음이의(a,b)는 비숫자."""
    return [int(n) for n in re.findall(r"\d+", lemma or "")]


def verse_text(velem):
    """단어 surface(형태소 구분 / 제거)를 이어붙여 절 본문 복원. seg(구두점) 포함."""
    out = []
    for ch in velem:
        tag = etree.QName(ch).localname
        if tag == "w":
            out.append((ch.text or "").replace("/", ""))
        elif tag == "seg":
            out.append(ch.text or "")
    return re.sub(r"\s+", " ", " ".join(p for p in out if p)).strip()


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    fv = open(os.path.join(OUTDIR, "wlc.jsonl"), "w", encoding="utf-8")
    fw = open(os.path.join(OUTDIR, "wlc_words.jsonl"), "w", encoding="utf-8")
    nv = nw = 0
    skipped, seen = [], set()
    usfm_to_osis = {v: k for k, v in OSIS_TO_USFM.items()}
    for bnum, code, name_kr, _ in BOOKS:          # BOOKS 순회 = book 정렬 보장
        osis = usfm_to_osis.get(code)
        path = os.path.join(WLC, f"{osis}.xml") if osis else None
        if not path or not os.path.exists(path):
            continue                              # NT(그리스어)는 WLC에 없음
        tree = etree.parse(path)
        seen.add(code)
        for v in tree.findall(".//o:verse", NS):  # 파일 내 verse는 장·절 순
            oid = v.get("osisID")
            m = re.match(r"(\w+)\.(\d+)\.(\d+)$", oid or "")
            if not m:
                skipped.append(oid); continue
            ch, vs = int(m.group(2)), int(m.group(3))
            fv.write(json.dumps({"book": bnum, "code": code, "name_kr": NAME_BY_CODE[code],
                                 "chapter": ch, "verse": vs, "text": verse_text(v),
                                 "source": "wlc"}, ensure_ascii=False) + "\n")
            nv += 1
            for wi, w in enumerate(v.findall("o:w", NS), 1):
                fw.write(json.dumps({"book": bnum, "code": code, "chapter": ch, "verse": vs,
                                     "w": wi, "surface": (w.text or "").replace("/", ""),
                                     "lemma": w.get("lemma"), "strong": strongs(w.get("lemma")),
                                     "morph": w.get("morph")}, ensure_ascii=False) + "\n")
                nw += 1
    fv.close(); fw.close()
    meta = {"source": "wlc", "books": len(seen), "verses": nv, "words": nw,
            "skipped": len(skipped)}
    json.dump(meta, open(os.path.join(OUTDIR, "_meta_wlc.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(meta, ensure_ascii=False))
    if skipped:
        print("skipped 예시:", skipped[:5])


if __name__ == "__main__":
    main()
