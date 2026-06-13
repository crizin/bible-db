#!/usr/bin/env python3
# /// script
# dependencies = ["google-genai", "numpy"]
# ///
"""절 본문 → Gemini Embedding 2 → int8 벡터 산출물 (로컬 1회 생성, API 키 필요).

대상은 검색 수요가 있는 한국어(krv)·영어(kjv)뿐. 산출물은 git에 커밋되어
build_db.py가 bible.sqlite의 vec0 테이블로 통합한다 → CI는 키 없이 재빌드 가능.

  GEMINI_API_KEY=... uv run scripts/embed_verses.py

벡터는 한 번 생성하면 verbatim 보존(텍스트 immutable 원칙의 derived 짝). 모델/차원을
바꿔 다시 뽑을 때만 재실행. 배치별 부분 결과(_partial/)로 중단 후 이어받기를 지원한다.
"""
import os, sys, json, time
import numpy as np
from google import genai
from google.genai import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "embeddings")
PARTIAL = os.path.join(OUT, "_partial")

MODEL = "gemini-embedding-2"
DIM = 768
BATCH = 100          # texts per request
RETRIES = 6

# 임베딩 대상 (순서 고정 — npy 행 순서가 곧 meta 행 순서).
SOURCES = [("krv", "krv/krv_holybible.jsonl"),
           ("kjv", "kjv/kjv.jsonl")]

NPY = os.path.join(OUT, "verses.gemini2-768.int8.npy")
META = os.path.join(OUT, "verses.meta.jsonl")


def jsonl(rel):
    for line in open(os.path.join(DATA, rel), encoding="utf-8"):
        line = line.strip()
        if line:
            yield json.loads(line)


def load_items():
    """[(source, book, chapter, verse, text)] in fixed order."""
    items = []
    for src, rel in SOURCES:
        for o in jsonl(rel):
            items.append((src, o["book"], o["chapter"], o["verse"], o["text"]))
    return items


def to_int8(vecs):
    """L2 정규화(이미 정규화돼 있어도 무해) 후 [-127,127] int8 양자화. cosine용."""
    vecs = np.asarray(vecs, dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    vecs = vecs / np.clip(norms, 1e-12, None)
    return np.clip(np.round(vecs * 127.0), -127, 127).astype(np.int8)


def embed_batch(client, texts):
    """문서는 instruction 없이 본문 그대로 임베딩(검색 대상). 지수 백오프 재시도.

    각 텍스트를 Content로 감싸야 입력당 1개씩 임베딩이 나온다(그냥 리스트로 주면
    gemini-embedding-2는 전체를 1개로 합쳐버린다).
    """
    cfg = types.EmbedContentConfig(output_dimensionality=DIM)
    contents = [types.Content(parts=[types.Part.from_text(text=t)]) for t in texts]
    last = None
    for t in range(RETRIES):
        try:
            resp = client.models.embed_content(model=MODEL, contents=contents, config=cfg)
            if len(resp.embeddings) != len(texts):
                raise RuntimeError(f"expected {len(texts)} embeddings, got {len(resp.embeddings)}")
            return np.array([e.values for e in resp.embeddings], dtype=np.float32)
        except Exception as e:  # noqa: BLE001 — 일시적 rate limit/네트워크 재시도
            last = e
            wait = 2 ** t
            print(f"  retry {t+1}/{RETRIES} after {wait}s: {e}", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"embed failed after {RETRIES} tries: {last}")


def main():
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        sys.exit("set GEMINI_API_KEY (or GOOGLE_API_KEY) first")
    os.makedirs(PARTIAL, exist_ok=True)

    items = load_items()
    n = len(items)
    nb = (n + BATCH - 1) // BATCH
    print(f"items: {n}  batches: {nb} (x{BATCH})  model: {MODEL}  dim: {DIM}")

    client = genai.Client()
    for b in range(nb):
        pf = os.path.join(PARTIAL, f"{b:05d}.npy")
        if os.path.exists(pf):
            continue
        texts = [it[4] for it in items[b * BATCH:(b + 1) * BATCH]]
        vecs = to_int8(embed_batch(client, texts))
        np.save(pf, vecs)
        done = min((b + 1) * BATCH, n)
        print(f"  [{done}/{n}] batch {b+1}/{nb}")

    arr = np.concatenate([np.load(os.path.join(PARTIAL, f"{b:05d}.npy")) for b in range(nb)])
    assert arr.shape == (n, DIM) and arr.dtype == np.int8, (arr.shape, arr.dtype)
    np.save(NPY, arr)

    with open(META, "w", encoding="utf-8") as f:
        f.write(json.dumps({"_meta": True, "model": MODEL, "dim": DIM, "quant": "int8",
                            "normalized": True, "count": n,
                            "sources": [s for s, _ in SOURCES]}, ensure_ascii=False) + "\n")
        for src, bk, ch, vs, _ in items:
            f.write(json.dumps({"source": src, "book": bk, "chapter": ch, "verse": vs}) + "\n")

    print(f"\nwrote {os.path.relpath(NPY, ROOT)}  {arr.shape} {arr.dtype} "
          f"({arr.nbytes // 1024 // 1024} MB)")
    print(f"wrote {os.path.relpath(META, ROOT)}  ({n} rows + header)")
    print("partial batches kept in _partial/ — safe to delete after verifying.")


if __name__ == "__main__":
    main()
