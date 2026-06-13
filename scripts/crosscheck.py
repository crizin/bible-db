#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""두 소스(holybible / bskorea) 개역한글 JSONL을 절 단위로 크로스체크.

- 절 키(book,chapter,verse) 집합 차이 = 절 분할/누락 차이
- 공통 절의 text 불일치 = 디지털화 차이 (사람이 확정할 후보)

raw 비교(완전 일치) + norm 비교(공백·문장부호 제거 후) 둘 다 본다.
norm까지 다르면 실제 글자 차이라 우선순위 높음.
출력: data/krv/crosscheck_report.txt
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from books import NAME_BY_CODE  # noqa

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.normpath(os.path.join(HERE, "..", "data", "krv"))
H = os.path.join(OUTDIR, "krv_holybible.jsonl")
B = os.path.join(OUTDIR, "krv_bskorea.jsonl")
REPORT = os.path.join(OUTDIR, "crosscheck_report.txt")

CODE_BY_NUM = {}  # book num → code (첫 등장 기록)


def load(path):
    d = {}
    for line in open(path, encoding="utf-8"):
        o = json.loads(line)
        d[(o["book"], o["chapter"], o["verse"])] = o["text"]
        CODE_BY_NUM[o["book"]] = o["code"]
    return d


def norm(s):
    # 공백 + 흔한 문장부호 제거 후 비교 (정제 차이/구두점 차이 무시)
    return re.sub(r"[\s.,·:;~!?()'\"\-]", "", s)


def ref(k):
    b, c, v = k
    return f"{CODE_BY_NUM.get(b, b)} {c}:{v}"


def main():
    if not (os.path.exists(H) and os.path.exists(B)):
        print("두 JSONL이 아직 다 없음:", os.path.exists(H), os.path.exists(B))
        return
    h, b = load(H), load(B)
    hk, bk = set(h), set(b)
    common = hk & bk
    honly = sorted(hk - bk)
    bonly = sorted(bk - hk)

    diff_raw, diff_norm = [], []
    for k in sorted(common):
        if h[k] != b[k]:
            diff_raw.append(k)
            if norm(h[k]) != norm(b[k]):
                diff_norm.append(k)

    lines = []
    lines.append("=== 개역한글 크로스체크 (holybible vs bskorea) ===")
    lines.append(f"holybible 절수: {len(h)}")
    lines.append(f"bskorea   절수: {len(b)}")
    lines.append(f"공통 절: {len(common)}")
    lines.append(f"holybible에만 있는 절: {len(honly)}")
    lines.append(f"bskorea에만 있는 절: {len(bonly)}")
    lines.append(f"text 불일치(raw): {len(diff_raw)}")
    lines.append(f"text 불일치(norm, 공백·구두점 제거 후에도 다름): {len(diff_norm)}")
    lines.append("")

    if honly:
        lines.append(f"--- holybible에만 있는 절 ({len(honly)}) ---")
        for k in honly[:200]:
            lines.append(f"  {ref(k)}  | {h[k]}")
        lines.append("")
    if bonly:
        lines.append(f"--- bskorea에만 있는 절 ({len(bonly)}) ---")
        for k in bonly[:200]:
            lines.append(f"  {ref(k)}  | {b[k]}")
        lines.append("")

    lines.append(f"--- text 불일치(norm) 전체 ({len(diff_norm)}) ---")
    for k in diff_norm:
        lines.append(f"  {ref(k)}")
        lines.append(f"    H: {h[k]}")
        lines.append(f"    B: {b[k]}")
    lines.append("")
    lines.append(f"--- text 불일치(raw만, 공백/구두점 차이) 샘플 ({len(diff_raw)-len(diff_norm)} 중 50) ---")
    raw_only = [k for k in diff_raw if k not in set(diff_norm)]
    for k in raw_only[:50]:
        lines.append(f"  {ref(k)}")
        lines.append(f"    H: {h[k]}")
        lines.append(f"    B: {b[k]}")

    open(REPORT, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines[:9]))
    print(f"\n전체 리포트: {REPORT}")


if __name__ == "__main__":
    main()
