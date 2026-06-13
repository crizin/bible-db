#!/usr/bin/env python3
# /// script
# dependencies = ["beautifulsoup4", "lxml"]
# ///
"""bible.bskorea.or.kr 개역한글(KRV) 크롤러.

URL: /bible/KRV/{usfm_code}.{장}  (Angular SSR, 본문이 정적 HTML에 포함)
파싱: <span class="verse ... KRV.GEN.1.1" data-verse-org-id="GEN.1.1">
      내부 <ibep-verse-text-renderer>에 본문 → 절번호 자동 배제.
출력: data/krv/krv_bskorea.jsonl  (FORMAT.md 스키마)

robots.txt가 AI봇을 명시 차단하는 사이트라 매너를 보수적으로:
  - sleep 1.5초, 순차 1개씩, 회피 트릭 없음
  - 연속 차단/에러(403/429/503) 누적되면 즉시 중단하고 보고
이어받기 지원.
"""
import json, os, sys, time, re, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup as BS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from books import BOOKS, clean

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.normpath(os.path.join(HERE, "..", "data", "krv"))
OUT = os.path.join(OUTDIR, "krv_bskorea.jsonl")
META = os.path.join(OUTDIR, "_meta_bskorea.json")
SLEEP = 1.5              # bskorea는 더 보수적으로
ABORT_AFTER = 5         # 연속 차단/에러 누적 시 중단
KST = timezone(timedelta(hours=9))

G1 = "태초에 하나님이 천지를 창조하시니라"
G2 = "땅이 혼돈하고 공허하며 흑암이 깊음 위에 있고 하나님의 신은 수면에 운행하시니라"

NAME_BY_NUM = {num: name for num, _, name, _ in BOOKS}


def fetch(code, cn):
    url = f"https://bible.bskorea.or.kr/bible/KRV/{code}.{cn}"
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "ko-KR,ko;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def parse(html):
    """반환: [(usfm_code, chapter, verse, text), ...]

    같은 data-verse-org-id가 여러 span.verse로 쪼개져 나온다(긴 절을 줄 단위로
    분할 표시). 같은 절 id의 조각을 등장 순서대로 이어붙여 완전한 절로 복원한다.
    """
    soup = BS(html, "lxml")
    acc, order = {}, []
    for sp in soup.select("span.verse"):
        org = sp.get("data-verse-org-id") or ""
        m = re.match(r"([A-Za-z0-9]+)\.(\d+)\.(\d+)", org)
        if not m:
            continue
        key = (m.group(1), int(m.group(2)), int(m.group(3)))
        renderer = sp.find("ibep-verse-text-renderer")
        text = clean(renderer if renderer else sp)
        if not text:
            continue
        if key not in acc:
            acc[key] = []
            order.append(key)
        acc[key].append(text)
    return [(c, ch, vs, " ".join(acc[(c, ch, vs)])) for c, ch, vs in order]


def load_done():
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT, encoding="utf-8"):
            try:
                o = json.loads(line)
                done.add((o["book"], o["chapter"]))
            except Exception:
                pass
    return done


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    done = load_done()
    failed = []
    consecutive = 0
    fout = open(OUT, "a", encoding="utf-8")
    aborted = False
    for bnum, code, name, nchap in BOOKS:
        if aborted:
            break
        for cn in range(1, nchap + 1):
            if (bnum, cn) in done:
                continue
            ok = False
            for attempt in range(2):
                try:
                    parsed = parse(fetch(code, cn))
                    if not parsed:
                        raise ValueError("0 verses parsed")
                    for pcode, pch, pvs, txt in parsed:
                        fout.write(json.dumps({
                            "book": bnum, "code": code, "name_kr": name,
                            "chapter": pch, "verse": pvs, "text": txt,
                            "source": "bskorea",
                        }, ensure_ascii=False) + "\n")
                    fout.flush()
                    print(f"OK {code} {cn} ({len(parsed)}v)", file=sys.stderr)
                    ok = True
                    consecutive = 0
                    break
                except urllib.error.HTTPError as e:
                    print(f"  HTTP {e.code} {code} {cn} ({attempt+1})", file=sys.stderr)
                    if e.code in (403, 429, 503):       # 차단 신호
                        consecutive += 1
                    time.sleep(5)
                except Exception as e:
                    print(f"  retry {code} {cn} ({attempt+1}): {e}", file=sys.stderr)
                    time.sleep(3)
            if not ok:
                failed.append({"book": bnum, "code": code, "chapter": cn})
                print(f"FAIL {code} {cn}", file=sys.stderr)
                consecutive += 1
            if consecutive >= ABORT_AFTER:
                print(f"\n⚠️ 연속 {consecutive}회 차단/실패 — 중단. 사이트를 두드리지 않음.",
                      file=sys.stderr)
                aborted = True
                break
            time.sleep(SLEEP)
    fout.close()
    finalize(failed, aborted)


def finalize(failed, aborted):
    rows = [json.loads(l) for l in open(OUT, encoding="utf-8")]
    rows.sort(key=lambda r: (r["book"], r["chapter"], r["verse"]))
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    chapters = {(r["book"], r["chapter"]) for r in rows}
    by_cv = {(r["code"], r["chapter"], r["verse"]): r["text"] for r in rows}
    g1 = by_cv.get(("GEN", 1, 1))
    g2 = by_cv.get(("GEN", 1, 2))
    meta = {
        "source": "bskorea",
        "version": "개역한글판 (KRV)",
        "crawled_at": datetime.now(KST).isoformat(),
        "aborted": aborted,
        "books": len({r["book"] for r in rows}),
        "chapters": len(chapters),
        "verses": len(rows),
        "failed": failed,
        "golden": {"GEN1:1_ok": g1 == G1, "GEN1:2_ok": g2 == G2,
                   "GEN1:2_is_sin": (g2 or "").find("하나님의 신") >= 0},
    }
    json.dump(meta, open(META, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n=== bskorea 완료 ===", file=sys.stderr)
    print(json.dumps(meta["golden"], ensure_ascii=False), file=sys.stderr)
    print(f"books={meta['books']} chapters={meta['chapters']} "
          f"verses={meta['verses']} failed={len(failed)} aborted={aborted}", file=sys.stderr)


if __name__ == "__main__":
    main()
