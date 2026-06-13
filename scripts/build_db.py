#!/usr/bin/env python3
# /// script
# dependencies = ["sqlite-vec", "numpy"]
# ///
"""모든 파싱 산출물을 SQLite(bible.sqlite)로 통합.

verses: 개역한글·KJV·WLC·byztxt 절 본문
words/word_strong: 원어 단어별 + Strong 연결 (wlc→H, byz→G)
strongs: 사전, strong_category: 의미 카테고리, tagnt_words: 판본비교
"""
import sqlite3, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from books import BOOKS
from versification import load_org_to_canon, to_canon, krv_to_canon

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")
DB = os.path.join(DATA, "bible.sqlite")

SCHEMA = """
CREATE TABLE books(book INTEGER PRIMARY KEY, code TEXT, name_kr TEXT, testament TEXT);
CREATE TABLE verses(id INTEGER PRIMARY KEY, book INT, chapter INT, verse INT, canon_chapter INT, canon_verse INT, source TEXT, text TEXT);
CREATE TABLE words(id INTEGER PRIMARY KEY, book INT, chapter INT, verse INT, canon_chapter INT, canon_verse INT, w INT, source TEXT, surface TEXT, morph TEXT);
CREATE TABLE word_strong(word_id INT, strong TEXT);
CREATE TABLE strongs(strong TEXT PRIMARY KEY, lang TEXT, lemma TEXT, translit TEXT, pron TEXT, derivation TEXT, strongs_def TEXT, kjv_def TEXT);
CREATE TABLE strong_category(strong TEXT, category TEXT, is_primary INT);
CREATE TABLE tagnt_words(book INT, chapter INT, verse INT, w INT, surface TEXT, translit TEXT, dstrong TEXT, morph TEXT, lemma TEXT, editions TEXT, gloss TEXT);
CREATE INDEX idx_verses_ref ON verses(book,chapter,verse);
CREATE INDEX idx_verses_canon ON verses(book,canon_chapter,canon_verse);
CREATE INDEX idx_verses_src ON verses(source);
CREATE INDEX idx_words_ref ON words(book,chapter,verse);
CREATE INDEX idx_words_canon ON words(book,canon_chapter,canon_verse);
CREATE INDEX idx_ws_word ON word_strong(word_id);
CREATE INDEX idx_ws_strong ON word_strong(strong);
CREATE INDEX idx_sc_strong ON strong_category(strong);
CREATE INDEX idx_sc_cat ON strong_category(category);
CREATE INDEX idx_tagnt_ref ON tagnt_words(book,chapter,verse);
"""


def jsonl(rel):
    p = os.path.join(DATA, rel)
    if not os.path.exists(p):
        return
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line:
            yield json.loads(line)


EMB_NPY = os.path.join(DATA, "embeddings", "verses.gemini2-768.int8.npy")
EMB_META = os.path.join(DATA, "embeddings", "verses.meta.jsonl")


def attach_vectors(conn, cur):
    """embed_verses.py 산출물이 있으면 sqlite-vec의 vec0 테이블로 통합한다.

    없으면 조용히 스킵 → 텍스트 전용 빌드와 100% 하위호환. 벡터는 derived 레이어로,
    canonical은 어디까지나 JSONL 본문과 커밋된 int8 npy.
    """
    if not (os.path.exists(EMB_NPY) and os.path.exists(EMB_META)):
        print("embeddings: none — vec_verses 생략 (텍스트 전용 빌드)")
        return
    import numpy as np
    import sqlite_vec

    arr = np.load(EMB_NPY)
    lines = [json.loads(x) for x in open(EMB_META, encoding="utf-8") if x.strip()]
    head, rows = lines[0], lines[1:]
    assert head.get("_meta") and head["count"] == len(rows) == arr.shape[0], "meta/npy 불일치"
    dim = head["dim"]

    # (source, book, chapter, verse) → verses.id 역참조 (절은 소스별 유일).
    id_map = {(s, b, c, v): i for i, b, c, v, s in
              cur.execute("SELECT id,book,chapter,verse,source FROM verses")}

    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    cur.execute(f"CREATE VIRTUAL TABLE vec_verses USING vec0("
                f"verse_id INTEGER PRIMARY KEY, embedding int8[{dim}] distance_metric=cosine)")

    ins, missing = [], 0
    for vec, m in zip(arr, rows):
        vid = id_map.get((m["source"], m["book"], m["chapter"], m["verse"]))
        if vid is None:
            missing += 1
            continue
        ins.append((vid, vec.tobytes()))
    cur.executemany("INSERT INTO vec_verses(verse_id, embedding) VALUES(?, vec_int8(?))", ins)
    print(f"vec_verses: {len(ins)}  ({head['model']} {dim}d int8)"
          + (f"  WARN missing={missing}" if missing else ""))


def main():
    if os.path.exists(DB):
        os.remove(DB)
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)
    cur = conn.cursor()

    cur.executemany("INSERT INTO books VALUES(?,?,?,?)",
                    [(n, c, nm, "OT" if n <= 39 else "NT") for n, c, nm, _ in BOOKS])

    # WLC(히브리)만 원본 좌표가 canonical(KJV)과 어긋난다 → canonical 좌표를 별도 부여.
    # kjv·krv는 canonical 기준 자체, byz(TR)는 NT라 매핑 룰이 없어 모두 identity.
    org2canon = load_org_to_canon()
    code_by_book = {n: c for n, c, _, _ in BOOKS}

    VSRC = {"krv": "krv/krv_holybible.jsonl",
            "kjv": "kjv/kjv.jsonl", "wlc": "hebrew/wlc.jsonl", "byz": "greek/byz.jsonl"}
    for src, rel in VSRC.items():
        rows = []
        for o in jsonl(rel):
            ch, vs = o["chapter"], o["verse"]
            code = code_by_book[o["book"]]
            if src == "wlc":
                cch, cv = to_canon(org2canon, code, ch, vs)
            elif src == "krv":
                cch, cv = krv_to_canon(code, ch, vs)
            else:
                cch, cv = ch, vs
            rows.append((o["book"], ch, vs, cch, cv, src, o["text"]))
        cur.executemany("INSERT INTO verses(book,chapter,verse,canon_chapter,canon_verse,source,text) "
                        "VALUES(?,?,?,?,?,?,?)", rows)
        print(f"verses[{src}]: {len(rows)}")

    wid = 0
    for src, rel, pref in [("wlc", "hebrew/wlc_words.jsonl", "H"), ("byz", "greek/byz_words.jsonl", "G")]:
        words, ws = [], []
        for o in jsonl(rel):
            wid += 1
            ch, vs = o["chapter"], o["verse"]
            cch, cv = to_canon(org2canon, code_by_book[o["book"]], ch, vs) if src == "wlc" else (ch, vs)
            words.append((wid, o["book"], ch, vs, cch, cv, o["w"], src,
                          o["surface"], o.get("morph")))
            for n in o.get("strong", []):
                ws.append((wid, f"{pref}{n}"))
        cur.executemany("INSERT INTO words VALUES(?,?,?,?,?,?,?,?,?,?)", words)
        cur.executemany("INSERT INTO word_strong VALUES(?,?)", ws)
        print(f"words[{src}]: {len(words)}  word_strong: {len(ws)}")

    for fn, lang in [("strongs/strongs_hebrew.json", "he"), ("strongs/strongs_greek.json", "gr")]:
        d = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
        cur.executemany("INSERT INTO strongs VALUES(?,?,?,?,?,?,?,?)",
                        [(k, lang, e.get("lemma"), e.get("xlit") or e.get("translit"),
                          e.get("pron"), e.get("derivation"), e.get("strongs_def"),
                          e.get("kjv_def")) for k, e in d.items()])

    sc = []
    for o in jsonl("categories/strong_categories.jsonl"):
        for c in o["categories"]:
            sc.append((o["strong"], c, 1 if c == o["primary"] else 0))
    cur.executemany("INSERT INTO strong_category VALUES(?,?,?)", sc)

    tg = [(o["book"], o["chapter"], o["verse"], o["w"], o["surface"], o.get("translit"),
           o.get("dstrong"), o.get("morph"), o.get("lemma"), o.get("editions"), o.get("gloss"))
          for o in jsonl("greek/tagnt_words.jsonl")]
    cur.executemany("INSERT INTO tagnt_words VALUES(?,?,?,?,?,?,?,?,?,?,?)", tg)
    conn.commit()

    attach_vectors(conn, cur)
    conn.commit()

    print("\n=== 테이블 행 수 ===")
    for t in ["books", "verses", "words", "word_strong", "strongs", "strong_category", "tagnt_words"]:
        print(f"  {t:18} {cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")
    print(f"\nDB: {os.path.relpath(DB, ROOT)}  ({os.path.getsize(DB)//1024//1024} MB)")
    conn.close()


if __name__ == "__main__":
    main()
