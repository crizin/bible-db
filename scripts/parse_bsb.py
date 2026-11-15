#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""Berean Standard Bible 공식 평문(bsb.txt) → 공통 JSONL.

원본: https://bereanbible.com/bsb.txt (https://berean.bible/downloads.htm 의
"Berean Standard Bible - Text"). 없으면 data/sources/bsb/ 에 받아 오고, 응답 헤더를
옆에 남겨 _meta_bsb.json 에 판본 정보로 옮긴다.

bsb.txt 는 이미 절 단위 평문이다 — "Book C:V<TAB>본문" 한 줄이 한 절이고, 소제목·교차참조·
각주·문단/시 행 기호·시편 119 의 히브리 자모 머리는 배포본에 없다. 시편 표제는 배포본이
1절 본문 앞에 붙여 둔 그대로 둔다(Ps 3:1 = 표제 + 1절). 걷어내는 것은 파일 머리의 BOM,
CRLF 줄바꿈, 머리 3줄(헌정 문구 2줄 + "Verse<TAB>Berean Standard Bible" 열 이름 줄)뿐이고
절 본문은 바이트 그대로 싣는다(공백 정규화도 하지 않는다).

배포본은 KJV 와 같은 31,102개 절 번호를 다 갖고 있고, 비평 본문에서 빠진 절(MAT 17:21 등)은
번호만 있고 본문이 비어 있다 — 그 절도 배포본 그대로 text="" 로 싣는다.
출력: data/bsb/bsb.jsonl (source="bsb"), data/bsb/_meta_bsb.json
"""
import hashlib, json, os, re, sys, urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from books import BOOKS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SRCDIR = os.path.join(ROOT, "data", "sources", "bsb")
RAW = os.path.join(SRCDIR, "bsb.txt")
RAW_HTTP = RAW + ".http.json"
OUTDIR = os.path.join(ROOT, "data", "bsb")
OUT = os.path.join(OUTDIR, "bsb.jsonl")
META = os.path.join(OUTDIR, "_meta_bsb.json")

URL = "https://bereanbible.com/bsb.txt"
DOWNLOADS_PAGE = "https://berean.bible/downloads.htm"
LICENSE_PAGE = "https://berean.bible/licensing.htm"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# downloads.htm 이 이 파일을 싣는 판(3rd Printing)은 아래 sha256 의 파일로 확인했다. 받은 파일이
# 다르면 판 표기를 다시 확인해야 하므로 edition 을 비워 둔다.
EDITION = "Current, updated to 3rd Printing"
EDITION_SHA256 = "2ac3af1de52d4e68261cba91d85c320b7eadc6560e830d99e591767b8ff5ca96"

COLUMNS = "Verse\tBerean Standard Bible"
# bsb.txt 의 책 이름 → BOOKS 순서(1..66). 배포본 등장 순서도 이 순서여야 한다.
BSB_NAMES = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
    "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalm", "Proverbs", "Ecclesiastes", "Song of Solomon",
    "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah",
    "Malachi", "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians",
    "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians",
    "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James",
    "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation",
]
REF = re.compile(r"^(.+) (\d+):(\d+)$")

G11 = "In the beginning God created the heavens and the earth."


def download():
    os.makedirs(SRCDIR, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
        http = {"url": URL, "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "last_modified": r.headers.get("Last-Modified"),
                "content_length": r.headers.get("Content-Length")}
    with open(RAW, "wb") as f:
        f.write(body)
    json.dump(http, open(RAW_HTTP, "w", encoding="utf-8"), indent=2)
    print(f"downloaded {URL} → {os.path.relpath(RAW, ROOT)} ({len(body)} bytes)")


def main():
    if not os.path.exists(RAW):
        download()
    raw = open(RAW, "rb").read()
    http = {}
    if os.path.exists(RAW_HTTP):
        http = json.load(open(RAW_HTTP, encoding="utf-8"))
    else:
        print(f"WARN: {os.path.relpath(RAW_HTTP, ROOT)} 없음 — fetched_at/last_modified 를 비워 둔다",
              file=sys.stderr)
    sha = hashlib.sha256(raw).hexdigest()

    text = raw.decode("utf-8")
    assert text.startswith("\ufeff"), "BOM 없음 — 배포 형식이 바뀌었는지 확인"
    lines = text[1:].split("\r\n")
    assert lines[-1] == "", "파일 끝이 CRLF 로 끝나지 않음"
    lines = lines[:-1]
    assert not any("\r" in l or "\n" in l for l in lines), "CRLF 아닌 줄바꿈 섞임"
    assert lines[2] == COLUMNS, f"열 이름 줄이 다름: {lines[2]!r}"
    attribution = [l.rstrip("\t") for l in lines[:2]]

    code_of = {name: BOOKS[i] for i, name in enumerate(BSB_NAMES)}
    out, seen, book_order = [], set(), []
    for n, line in enumerate(lines[3:], start=4):
        ref, tab, body = line.partition("\t")
        m = REF.match(ref)
        if not (tab and "\t" not in body and m and m.group(1) in code_of):
            sys.exit(f"line {n}: 형식 밖의 줄 {line[:80]!r}")
        bnum, code, name_kr, _ = code_of[m.group(1)]
        ch, vs = int(m.group(2)), int(m.group(3))
        key = (bnum, ch, vs)
        assert key not in seen, f"line {n}: 중복 절 {ref}"
        seen.add(key)
        if not book_order or book_order[-1] != bnum:
            book_order.append(bnum)
        out.append({"book": bnum, "code": code, "name_kr": name_kr,
                    "chapter": ch, "verse": vs, "text": body, "source": "bsb"})
    assert book_order == list(range(1, 67)), "책 순서가 BOOKS 와 다름"
    assert out == sorted(out, key=lambda r: (r["book"], r["chapter"], r["verse"])), "절 순서 어긋남"
    # 머리 3줄 + JSONL 행만으로 원본 파일이 바이트 그대로 다시 나와야 한다(본문 무손실 확인).
    rebuilt = "\ufeff" + "\r\n".join(lines[:3] + [
        f"{BSB_NAMES[r['book'] - 1]} {r['chapter']}:{r['verse']}\t{r['text']}" for r in out]) + "\r\n"
    if rebuilt.encode("utf-8") != raw:
        sys.exit("JSONL 행으로 bsb.txt 가 바이트 그대로 재구성되지 않음")

    os.makedirs(OUTDIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    chapters = {(r["book"], r["chapter"]) for r in out}
    chap_mismatch = []
    for bnum, code, _, nchap in BOOKS:
        got = len({c for b, c in chapters if b == bnum})
        if got != nchap:
            chap_mismatch.append({"code": code, "got": got, "expect": nchap})
    g = next(r["text"] for r in out if r["code"] == "GEN" and r["chapter"] == 1 and r["verse"] == 1)
    meta = {
        "source": "bsb",
        "version": "Berean Standard Bible (BSB)",
        "edition": EDITION if sha == EDITION_SHA256 else None,
        "url": http.get("url", URL),
        "downloads_page": DOWNLOADS_PAGE,
        "license_page": LICENSE_PAGE,
        "license": "Public Domain (dedicated 2023-04-30)",
        "fetched_at": http.get("fetched_at"),
        "last_modified": http.get("last_modified"),
        "bytes": len(raw),
        "sha256": sha,
        "attribution": attribution,
        "books": len(book_order),
        "chapters": len(chapters),
        "verses": len(out),
        "empty_verses": [f"{r['code']} {r['chapter']}:{r['verse']}" for r in out if r["text"] == ""],
        "chap_mismatch": chap_mismatch,
        "golden": {"GEN1:1_ok": g == G11, "GEN1:1": g},
    }
    if meta["edition"] is None:
        print(f"WARN: sha256 {sha} ≠ 확인된 판 — downloads.htm 의 판 표기를 다시 확인할 것",
              file=sys.stderr)
    json.dump(meta, open(META, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
