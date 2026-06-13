#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""WLC(히브리 원본) 절 좌표 → canonical(KJV/개신교) 좌표 매핑.

morphhb WLC는 히브리어(Leningrad) versification을 보존한다(parse_wlc.py 참고).
KJV·개역한글은 개신교/영어 스킴을 따르며 이 데이터셋의 canonical 기준이다.
시편 표제(superscription)·요엘/말라기 장 분할·일부 절 경계가 둘 사이에서 어긋나서,
한 좌표로 4개 언어 절을 정렬하려면 WLC 절에 canonical 좌표를 부여해야 한다.

매핑은 Copenhagen Alliance versification-specification(eng.json)에서 가져온다.
eng.json의 mappedVerses는 {canonical(eng) 좌표: 원본(org) 좌표}이며, 우리 66권
범위에서 (1) 책을 넘나드는 룰이 없고 (2) 모든 룰이 1:1 길이 정렬이다 — 순수 offset
shift(load 시 둘 다 검증). byz(Robinson-Pierpont)는 KJV와 versification이 같아 NT는
매핑 룰이 없고 항상 identity다. 개역한글(krv)도 대체로 KJV와 같으나 절 경계가 4곳에서
어긋나 별도 보정한다(KRV_CANON_FIX).
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from books import BOOKS

MAP_FILE = os.path.join(HERE, "..", "data", "versification", "eng.json")
OUR_CODES = {c for _, c, _, _ in BOOKS}        # 66권 — 외경(BAR/ESG…) 룰은 스킵
_REF = re.compile(r"^(\S+)\s+(\d+):(\d+)(?:-(\d+))?$")

# morphhb WLC ↔ Copenhagen "org" 차이 보정. eng.json은 외부 표준이라 verbatim 유지하고,
# morphhb 특유의 분절만 여기서 보정한다. NUM 25:19("염병 후에")는 morphhb가 별도 절로
# 분리한 곳으로 KJV 26:1 앞부분과 합쳐진다 — 정합 검증으로 확인된 유일한 morphhb↔org 차이.
_MORPHHB_FIXUP = {("NUM", 25, 19): (26, 1)}


def _expand(ref):
    """'PSA 3:0-8' → [('PSA',3,0),…,('PSA',3,8)]. 단일 절도 1개짜리 리스트로."""
    m = _REF.match(ref)
    if not m:
        raise ValueError(f"파싱 불가한 절 참조: {ref!r}")
    code, ch, a = m.group(1), int(m.group(2)), int(m.group(3))
    b = int(m.group(4)) if m.group(4) else a
    return [(code, ch, v) for v in range(a, b + 1)]


def load_org_to_canon(map_file=MAP_FILE):
    """org(WLC) 좌표 → canonical(eng) 좌표 dict: {(code, chapter, verse): (canon_chapter, canon_verse)}.

    identity 절은 담지 않는다(호출부에서 fallback). 책 넘나듦·길이 불일치는 즉시 에러 —
    매핑 가정이 깨지면 조용히 잘못된 정렬을 만드느니 빌드를 멈춘다.
    """
    mv = json.load(open(map_file, encoding="utf-8"))["mappedVerses"]
    out = {}
    for canon_ref, org_ref in mv.items():
        if canon_ref.split(" ", 1)[0] not in OUR_CODES:
            continue
        canon, org = _expand(canon_ref), _expand(org_ref)
        if len(canon) != len(org):
            raise ValueError(f"길이 불일치: {canon_ref}({len(canon)}) ≠ {org_ref}({len(org)})")
        for (oc, och, ov), (cc, cch, cv) in zip(org, canon):
            if oc != cc:
                raise ValueError(f"책을 넘나드는 룰: {org_ref} → {canon_ref}")
            out[(oc, och, ov)] = (cch, cv)

    # 2줄 표제 시편(예: 51·52·54·60): org 표제 1·2절 중 Copenhagen은 둘째 줄만
    # canon verse 0(표제)에 매핑하고 첫 줄(org n:1)은 룰에서 빠진다. 표제는 장 맨 앞
    # 연속 블록이므로, canon verse 0으로 가는 org 절 이하 같은 장 절은 전부 표제로 묶는다.
    title_max = {}
    for (oc, och, ov), (_, cv) in out.items():
        if cv == 0 and ov > title_max.get((oc, och), 0):
            title_max[(oc, och)] = ov
    for (oc, och), vmax in title_max.items():
        for ov in range(1, vmax + 1):
            out[(oc, och, ov)] = (och, 0)

    out.update(_MORPHHB_FIXUP)
    return out


def to_canon(org_map, code, chapter, verse):
    """WLC 좌표를 canonical로. 매핑에 없으면 identity."""
    return org_map.get((code, chapter, verse), (chapter, verse))


# 개역한글(krv)은 대체로 KJV versification을 따르나 절 경계가 4곳에서 어긋난다. krv 한 절이
# KJV 두 절을 합쳤거나(합침 → 그 장 이후 절 번호가 밀림), KJV 한 절을 둘로 나눈(분할 → 둘째
# 절을 같은 canon에 병합) 경우다. 합치는 쪽인 삼상 30:30(=KJV 30:30+31)·시 72:19(=KJV 72:19+20)는
# raw=canon이라 보정이 없고, 그 결과 KJV 30:31·72:20·고후 13:12는 krv 짝이 없다(정당한 병합).
KRV_CANON_FIX = {
    ("2CO", 13, 12): (13, 13),  # krv 11이 KJV 11+12를 합침 → 이후 +1 밀림
    ("2CO", 13, 13): (13, 14),
    ("SNG", 6, 14): (6, 13),    # KJV 6:13을 krv가 6:13+6:14로 분할 → 14는 canon 13에 병합
    ("3JN", 1, 15): (1, 14),    # KJV 1:14를 krv가 14+15로 분할 → 15는 canon 14에 병합
}


def krv_to_canon(code, chapter, verse):
    """개역한글 좌표를 canonical(KJV)로. 매핑에 없으면 identity."""
    return KRV_CANON_FIX.get((code, chapter, verse), (chapter, verse))


if __name__ == "__main__":
    m = load_org_to_canon()
    print(f"org→canon 매핑 엔트리: {len(m)}")
    for code, ch, vs in [("PSA", 3, 1), ("PSA", 3, 2), ("PSA", 51, 1), ("PSA", 51, 3),
                         ("NUM", 17, 1), ("NUM", 17, 16), ("MAL", 3, 19), ("JOL", 3, 1)]:
        print(f"  WLC {code} {ch}:{vs} → canon {to_canon(m, code, ch, vs)}")
    print(f"krv 보정 엔트리: {len(KRV_CANON_FIX)}")
    for code, ch, vs in [("2CO", 13, 12), ("2CO", 13, 13), ("SNG", 6, 14), ("3JN", 1, 15)]:
        print(f"  krv {code} {ch}:{vs} → canon {krv_to_canon(code, ch, vs)}")
