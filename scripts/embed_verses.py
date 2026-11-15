#!/usr/bin/env python3
# /// script
# dependencies = ["google-genai", "numpy"]
# ///
"""절 본문 → Gemini Embedding 2 → int8 벡터 산출물 (로컬 1회 생성, API 키 필요).

대상은 검색 수요가 있는 한국어(krv)·영어(bsb)뿐. 산출물은 git에 커밋되어
build_db.py가 bible.sqlite의 vec0 테이블로 통합한다 → CI는 키 없이 재빌드 가능.

  GEMINI_API_KEY=... uv run scripts/embed_verses.py [--fresh [SOURCE ...]]

벡터는 한 번 생성하면 verbatim 보존(텍스트 immutable 원칙의 derived 짝). Gemini는 비결정적이라
다시 뽑으면 값이 달라지므로, 기존 산출물이 같은 모델·차원이면 (source, book, chapter, verse)
키가 같고 meta 행의 sha(임베딩한 본문의 sha256 앞 16자리)가 지금 본문과 같은 행은 그대로 옮기고,
나머지(새 절·본문이 바뀐 절)만 새로 임베딩한다.
한 source를 통째로 다시 뽑으려면 --fresh <source>, 모델/차원을 바꿀 때는 --fresh(전부 새로).
본문이 빈 절(bsb의 번호만 있는 절)은 임베딩하지 않는다. 배치별 부분 결과(_partial/)로 중단 후
이어받기를 지원한다.
"""
import os, sys, json, time, hashlib, argparse
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
           ("bsb", "bsb/bsb.jsonl")]

NPY = os.path.join(OUT, "verses.gemini2-768.int8.npy")
META = os.path.join(OUT, "verses.meta.jsonl")


def jsonl(rel):
    for line in open(os.path.join(DATA, rel), encoding="utf-8"):
        line = line.strip()
        if line:
            yield json.loads(line)


def text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_items():
    """[(source, book, chapter, verse, text)] in fixed order. 빈 본문은 뺀다."""
    items = []
    for src, rel in SOURCES:
        for o in jsonl(rel):
            if o["text"]:
                items.append((src, o["book"], o["chapter"], o["verse"], o["text"]))
    return items


def load_existing():
    """같은 모델·차원의 기존 산출물 → {(source, book, chapter, verse): (int8 행, sha)}. 없으면 {}."""
    if not (os.path.exists(NPY) and os.path.exists(META)):
        return {}
    lines = [json.loads(x) for x in open(META, encoding="utf-8") if x.strip()]
    head, rows = lines[0], lines[1:]
    if (head.get("model"), head.get("dim"), head.get("quant")) != (MODEL, DIM, "int8"):
        print(f"existing vectors are {head.get('model')}/{head.get('dim')} — not reused")
        return {}
    arr = np.load(NPY)
    assert head["count"] == len(rows) == arr.shape[0], "meta/npy 불일치"
    return {(m["source"], m["book"], m["chapter"], m["verse"]): (vec, m.get("sha"))
            for m, vec in zip(rows, arr)}


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
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", nargs="*", metavar="SOURCE", choices=[s for s, _ in SOURCES],
                    help="기존 벡터를 재사용하지 않고 새로 임베딩할 source (생략하면 전부)")
    a = ap.parse_args()

    items = load_items()
    n = len(items)
    old = {} if a.fresh == [] else load_existing()
    if a.fresh:
        old = {k: v for k, v in old.items() if k[0] not in a.fresh}
    shas = {it[:4]: text_sha(it[4]) for it in items}
    keep = {k: old[k][0] for k in shas if k in old and old[k][1] == shas[k]}
    todo = [it for it in items if it[:4] not in keep]
    reused = n - len(todo)
    print(f"items: {n}  reused: {reused}  to embed: {len(todo)}  model: {MODEL}  dim: {DIM}")

    new = {}
    if todo:
        if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
            sys.exit("set GEMINI_API_KEY (or GOOGLE_API_KEY) first")
        # 부분 결과는 임베딩할 목록(키·본문·모델·차원)별 폴더에 — 하나라도 바뀌면 새 폴더.
        tag = hashlib.sha1(json.dumps([MODEL, DIM, [(*it[:4], shas[it[:4]]) for it in todo]])
                           .encode()).hexdigest()[:12]
        pdir = os.path.join(PARTIAL, tag)
        os.makedirs(pdir, exist_ok=True)
        nb = (len(todo) + BATCH - 1) // BATCH
        client = genai.Client()
        for b in range(nb):
            pf = os.path.join(pdir, f"{b:05d}.npy")
            if os.path.exists(pf):
                continue
            texts = [it[4] for it in todo[b * BATCH:(b + 1) * BATCH]]
            np.save(pf, to_int8(embed_batch(client, texts)))
            print(f"  [{min((b + 1) * BATCH, len(todo))}/{len(todo)}] batch {b+1}/{nb}")
        vecs = np.concatenate([np.load(os.path.join(pdir, f"{b:05d}.npy")) for b in range(nb)])
        assert vecs.shape == (len(todo), DIM), vecs.shape
        new = {it[:4]: v for it, v in zip(todo, vecs)}

    arr = np.stack([keep[it[:4]] if it[:4] in keep else new[it[:4]] for it in items])
    assert arr.shape == (n, DIM) and arr.dtype == np.int8, (arr.shape, arr.dtype)
    np.save(NPY, arr)

    with open(META, "w", encoding="utf-8") as f:
        f.write(json.dumps({"_meta": True, "model": MODEL, "dim": DIM, "quant": "int8",
                            "normalized": True, "count": n,
                            "sources": [s for s, _ in SOURCES]}, ensure_ascii=False) + "\n")
        for src, bk, ch, vs, _ in items:
            f.write(json.dumps({"source": src, "book": bk, "chapter": ch, "verse": vs,
                                "sha": shas[(src, bk, ch, vs)]}) + "\n")

    print(f"\nwrote {os.path.relpath(NPY, ROOT)}  {arr.shape} {arr.dtype} "
          f"({arr.nbytes // 1024 // 1024} MB)")
    print(f"wrote {os.path.relpath(META, ROOT)}  ({n} rows + header, {reused} reused)")
    if todo:
        print(f"partial batches kept in {os.path.relpath(pdir, ROOT)}/ — safe to delete after verifying.")


if __name__ == "__main__":
    main()
