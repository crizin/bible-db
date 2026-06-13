#!/usr/bin/env python3
# /// script
# dependencies = ["beautifulsoup4", "lxml"]
# ///
"""holybible.or.kr 개역한글(RHV) 크롤러.

URL: bibleftxt.php?VR=RHV&VL={1-66}&CN={장}&CV=99  (EUC-KR)
파싱: <li> + <font class=tk4l> = 한 절, li 순서 = 절번호.
출력: data/krv/krv_holybible.jsonl  (FORMAT.md 스키마)

이어받기 지원(이미 받은 book,chapter skip). 보수적 sleep, 순차 1개씩.
"""
import json, os, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup as BS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from books import BOOKS, clean

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.normpath(os.path.join(HERE, "..", "data", "krv"))
OUT = os.path.join(OUTDIR, "krv_holybible.jsonl")
META = os.path.join(OUTDIR, "_meta_holybible.json")
SLEEP = 0.7          # 요청 간 간격(초)
KST = timezone(timedelta(hours=9))

G1 = "태초에 하나님이 천지를 창조하시니라"
G2 = "땅이 혼돈하고 공허하며 흑암이 깊음 위에 있고 하나님의 신은 수면에 운행하시니라"


def fetch(vl, cn):
    url = (f"http://www.holybible.or.kr/B_RHV/cgi/bibleftxt.php"
           f"?VR=RHV&VL={vl}&CN={cn}&CV=99&KY=")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("euc-kr", errors="replace")


def parse(html):
    soup = BS(html, "lxml")
    lis = [li for li in soup.find_all("li") if li.find("font", class_="tk4l")]
    return [clean(li) for li in lis]


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
    fout = open(OUT, "a", encoding="utf-8")
    for bnum, code, name, nchap in BOOKS:
        for cn in range(1, nchap + 1):
            if (bnum, cn) in done:
                continue
            ok = False
            for attempt in range(2):
                try:
                    verses = parse(fetch(bnum, cn))
                    if not verses:
                        raise ValueError("0 verses parsed")
                    for i, txt in enumerate(verses, 1):
                        fout.write(json.dumps({
                            "book": bnum, "code": code, "name_kr": name,
                            "chapter": cn, "verse": i, "text": txt,
                            "source": "holybible",
                        }, ensure_ascii=False) + "\n")
                    fout.flush()
                    print(f"OK {code} {cn} ({len(verses)}v)", file=sys.stderr)
                    ok = True
                    break
                except Exception as e:
                    print(f"  retry {code} {cn} ({attempt+1}): {e}", file=sys.stderr)
                    time.sleep(3)
            if not ok:
                failed.append({"book": bnum, "code": code, "chapter": cn})
                print(f"FAIL {code} {cn}", file=sys.stderr)
            time.sleep(SLEEP)
    fout.close()
    finalize(failed)


def finalize(failed):
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
        "source": "holybible",
        "version": "개역한글판 (RHV)",
        "crawled_at": datetime.now(KST).isoformat(),
        "books": len({r["book"] for r in rows}),
        "chapters": len(chapters),
        "verses": len(rows),
        "failed": failed,
        "golden": {"GEN1:1_ok": g1 == G1, "GEN1:2_ok": g2 == G2,
                   "GEN1:2_is_sin": (g2 or "").find("하나님의 신") >= 0},
    }
    json.dump(meta, open(META, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n=== holybible 완료 ===", file=sys.stderr)
    print(json.dumps(meta["golden"], ensure_ascii=False), file=sys.stderr)
    print(f"books={meta['books']} chapters={meta['chapters']} "
          f"verses={meta['verses']} failed={len(failed)}", file=sys.stderr)


if __name__ == "__main__":
    main()
