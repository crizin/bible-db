#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""Strong 사전 엔트리를 의미 카테고리 분류용 배치 파일로 분할.

각 배치 = BATCH개 엔트리(strong/lemma/translit/def/kjv). 서브에이전트가 배치 하나씩
Read해서 taxonomy로 분류한다. 출력: data/categories/in/batch_NNN.jsonl
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
STR = os.path.join(ROOT, "data", "strongs")
OUTDIR = os.path.join(ROOT, "data", "categories", "in")
BATCH = 150


def load(path):
    d = json.load(open(path, encoding="utf-8"))
    rows = []
    for num, e in d.items():
        rows.append({
            "strong": num,
            "lemma": e.get("lemma", ""),
            "translit": e.get("xlit") or e.get("translit", ""),
            "def": e.get("strongs_def", ""),
            "kjv": e.get("kjv_def", ""),
        })
    return rows


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    entries = load(os.path.join(STR, "strongs_hebrew.json")) + \
        load(os.path.join(STR, "strongs_greek.json"))
    n = 0
    for i in range(0, len(entries), BATCH):
        with open(os.path.join(OUTDIR, f"batch_{n:03d}.jsonl"), "w", encoding="utf-8") as f:
            for e in entries[i:i + BATCH]:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        n += 1
    print(f"엔트리 {len(entries)} → 배치 {n}개 (배치당 {BATCH})")


if __name__ == "__main__":
    main()
