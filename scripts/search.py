#!/usr/bin/env python3
# /// script
# dependencies = ["google-genai", "numpy", "sqlite-vec"]
# ///
"""bible.sqlite의 vec0 벡터 색인으로 자연어 의미 검색 (데모).

  GEMINI_API_KEY=... uv run scripts/search.py "불안할 때 위로가 되는 말씀" --lang ko --k 10

쿼리도 문서와 똑같이 instruction 없이 임베딩한다(같은 벡터 공간 유지). Gemini Embedding 2는
cross-lingual이라 한국어 쿼리로 영어(KJV) 구절도, 영어 쿼리로 한국어 구절도 매칭된다.
결과는 canonical 좌표로 묶어 한/영을 나란히 보여준다.
"""
import os, sys, argparse, sqlite3
import numpy as np
import sqlite_vec
from google import genai
from google.genai import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
DB = os.path.join(ROOT, "data", "bible.sqlite")
MODEL = "gemini-embedding-2"
DIM = 768
SRC = {"ko": ("krv",), "en": ("kjv",), "all": ("krv", "kjv")}


def embed_query(text):
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        sys.exit("set GEMINI_API_KEY (or GOOGLE_API_KEY) first")
    client = genai.Client()
    resp = client.models.embed_content(
        model=MODEL, contents=text,
        config=types.EmbedContentConfig(output_dimensionality=DIM))
    v = np.array(resp.embeddings[0].values, dtype=np.float32)
    v = v / np.clip(np.linalg.norm(v), 1e-12, None)
    return np.clip(np.round(v * 127.0), -127, 127).astype(np.int8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--lang", choices=["ko", "en", "all"], default="all")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--db", default=DB)
    a = ap.parse_args()

    qv = embed_query(a.query)
    conn = sqlite3.connect(a.db)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    # 언어 필터는 KNN 후 적용 → lang!=all이면 후보를 넉넉히 당겨 상위 k를 채운다.
    pool = max(a.k * 3, 30) if a.lang != "all" else max(a.k, 10)
    knn = conn.execute(
        "SELECT verse_id, distance FROM vec_verses "
        "WHERE embedding MATCH vec_int8(?) AND k = ? ORDER BY distance",
        (qv.tobytes(), pool)).fetchall()

    wanted, seen, hits = set(SRC[a.lang]), set(), []
    for vid, dist in knn:
        row = conn.execute(
            "SELECT source, book, canon_chapter, canon_verse FROM verses WHERE id = ?",
            (vid,)).fetchone()
        if not row or row[0] not in wanted:
            continue
        key = row[1:]                       # (book, canon_chapter, canon_verse)
        if key in seen:
            continue
        seen.add(key)
        hits.append((dist, *key))
        if len(hits) >= a.k:
            break

    print(f'\nQ: "{a.query}"   (lang={a.lang}, k={a.k})\n')
    for rank, (dist, book, cch, cv) in enumerate(hits, 1):
        print(f"{rank:2}. [{dist:.3f}]")
        for source, code, ch, vs, text in conn.execute(
                "SELECT v.source, b.code, v.chapter, v.verse, v.text "
                "FROM verses v JOIN books b ON b.book = v.book "
                "WHERE v.book=? AND v.canon_chapter=? AND v.canon_verse=? "
                "AND v.source IN ('krv','kjv') ORDER BY v.source DESC",
                (book, cch, cv)):
            tag = "KR" if source.startswith("krv") else "EN"
            print(f"    {tag} {code} {ch}:{vs}  {text}")
    if not hits:
        print("  (no vec_verses — build with embeddings present, or check --lang)")


if __name__ == "__main__":
    main()
