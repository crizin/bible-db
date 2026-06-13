#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""분류 배치(out/batch_*.jsonl) 머지 + taxonomy 키 정규화/검증 + 분포.

에이전트가 minor만 쓴 경우(예: 'attitude_character') minor→'major>minor'로 자동 보정.
출력: data/categories/strong_categories.jsonl
"""
import json, glob, os, re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
CAT = os.path.join(ROOT, "data", "categories")


def valid_keys():
    keys = set()
    for line in open(os.path.join(CAT, "taxonomy.md"), encoding="utf-8").read().split("\n"):
        mm = re.match(r"\d+\.\s+\*\*(\w+)\*\*", line)
        if not mm:
            continue
        major = mm.group(1)
        keys.add(major)
        rest = line.split(":", 1)[1] if ":" in line else ""
        for minor in re.findall(r"([a-z_]+)\(", rest):
            keys.add(f"{major}>{minor}")
    return keys


def skey(s):
    return (s[0], int(s[1:]))


def main():
    valid = valid_keys()
    minor_to_full = {k.split(">")[1]: k for k in valid if ">" in k}

    def norm(c):
        if not c:
            return None
        if c in valid:
            return c
        if ">" in c:
            mj, mn = c.split(">", 1)
            if mn in minor_to_full:
                return minor_to_full[mn]      # 잘못된 major에 붙은 minor 교정
            return mj if mj in valid else None
        return minor_to_full.get(c)           # minor만 쓴 경우 → major>minor

    seen, unfixable = {}, Counter()
    for path in sorted(glob.glob(os.path.join(CAT, "out", "batch_*.jsonl"))):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            cats = []
            for c in o.get("categories", []):
                n = norm(c)
                if n and n not in cats:
                    cats.append(n)
                elif not n:
                    unfixable[c] += 1
            p = norm(o.get("primary", ""))
            o["categories"] = cats or ([p] if p else ["abstract_quality"])
            o["primary"] = p or o["categories"][0]
            seen[o["strong"]] = o

    out = os.path.join(CAT, "strong_categories.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for s in sorted(seen, key=skey):
            f.write(json.dumps(seen[s], ensure_ascii=False) + "\n")

    major = Counter(o["primary"].split(">")[0] for o in seen.values())
    print(f"unique strong: {len(seen)} (기대 14197)")
    print(f"보정 후 못 고친 키: {len(unfixable)}종 / {sum(unfixable.values())}건  {dict(unfixable) if unfixable else ''}")
    print(f"\n대분류 분포 (primary):")
    for k, v in major.most_common():
        print(f"  {k:24} {v}")


if __name__ == "__main__":
    main()
