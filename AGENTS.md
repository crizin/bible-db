# AGENTS.md

Guidance for AI agents working **in** this repo. (For *using* the data, see README.)

## ⚠️ Texts are immutable — never AI-generate or "correct" them

The `text` (verses) and `surface` (words) columns are collected **verbatim** from
verified public-domain / openly-licensed sources. An agent must **never** generate,
edit, "fix typos", paraphrase, or guess biblical text. What looks like a typo is
usually the source's digitization or original-language orthography. The integrity
of this dataset is its entire value — one silent "improvement" poisons it.

The machine-generated layers are `strong_category` (semantic tags, grounded in Strong's
lemmas/definitions, not invented) and `vec_verses` (verse embeddings from Gemini Embedding 2).
Both are **derived** — they never alter the verbatim `text`/`surface` columns.

If a text genuinely needs a fix: human review + re-verification against the source
first. Never silently.

## Source of truth

- **JSONL is canonical; `bible.sqlite` is a build artifact.** Never edit the DB
  directly — fix the JSONL and rebuild: `uv run scripts/build_db.py`.
- The committed int8 vectors under `data/embeddings/` are canonical too: Gemini is
  non-deterministic, so re-running gives *different* vectors — the generated set is
  preserved verbatim (like the texts), and `build_db.py` folds it into `vec_verses`.
- `data/sources/` (upstream clones) are **not** committed — parse scripts fetch them.
- Verse `source` values: `krv` (Korean 개역한글, from holybible.or.kr) · `kjv` ·
  `wlc` (Hebrew) · `byz` (Greek). A second Korean crawl (bskorea) is diffed at build
  time by `crosscheck.py` for verification but **not** loaded into the DB.

## Regeneration workflow

- Texts: `crawl_*.py` / `parse_*.py` → JSONL → `build_db.py`
  (Korean also: `crosscheck.py` to diff the two crawls)
- Categories: `split_strongs.py` → batch classification (follow `taxonomy.md`) →
  `merge_categories.py` (normalizes + validates taxonomy keys)
- Vectors: `embed_verses.py` (ko+en verses → Gemini Embedding 2, 768-d int8, **needs
  `GEMINI_API_KEY`**) → commits `data/embeddings/verses.*.int8.npy` + `verses.meta.jsonl`
  → `build_db.py` folds them into `vec_verses`. Regenerate **only** to change model/dim.
- `build_db.py` reads only JSONL + committed vectors — no `data/sources/`, no API key —
  so CI builds the full DB (text + `vec_verses`).

## Gotchas

- **Versification**: original (`wlc`) coordinates stay in `chapter`/`verse`; `build_db.py`
  adds a canonical KJV coordinate in `canon_chapter`/`canon_verse` via `versification.py`
  (Copenhagen `eng.json`, org→KJV). **Join across languages on the canonical coordinate**,
  not the raw verse key. Psalm titles → `canon_verse=0`; one canonical verse can hold 2
  Hebrew verses where KJV merges (Num 26:1), and a few KJV verses have no Hebrew counterpart
  where English splits one (Neh 7:68, Ps 13:6, Isa 64:1). Num 25:19 is the one morphhb↔org
  divergence, fixed up in `versification.py`. **krv** is mostly KJV-aligned but its verse
  boundaries differ in 4 spots, fixed in `KRV_CANON_FIX`: krv merges two KJV verses (1Sa
  30:30, Ps 72:19) leaving KJV 30:31/72:20 without a krv counterpart, and 2Co 13 shifts up
  by one after krv 11 absorbs KJV 13:12; krv splits one KJV verse in two (Song 6:13→krv
  6:13+6:14, 3Jn 1:14→krv 1:14+1:15), both folding back onto the one KJV canon coordinate.
- **Strong prefix**: `word_strong.strong` is `H####` (Hebrew/wlc) or `G####`
  (Greek/byz); dictionary keys match. WLC lemma `b/7225` = morpheme `b` + Strong
  `7225` — extract digits only.
- **TAGNT**: STEPBible asks not to redistribute. `tagnt_words` data is **not**
  bundled — users run `parse_tagnt.py` themselves. Do not commit it.
- **Categories**: multi-label with one `is_primary` (the main sense). Polysemous
  words span several categories; `is_primary=1` is the precision lever for search.
- **Vectors**: `vec_verses` is a `sqlite-vec` `vec0` table (int8, cosine) — load the
  extension (`sqlite_vec.load`) to query it; `verse_id` maps to `verses.id`. Only ko+en
  are embedded. gemini-embedding-2 collapses a plain list into **one** embedding — wrap
  each text in a `types.Content` to get one per verse (see `embed_verses.py`). 768-d
  output is already L2-normalized. Query the same way you embedded (plain text, no
  task instruction) to stay in one space.

## Verify after any data change

- Golden samples: Gen 1:1; **Gen 1:2 Korean must read "하나님의 신"** — if it reads
  "하나님의 영" that's 개역개정 (copyrighted!), not 개역한글 — stop immediately.
- Counts: Korean ~31,100 verses, KJV 31,102, 66 books, 1,189 chapters.
- Category keys: only `major>minor` from `taxonomy.md` (merge_categories validates).
- Versification: every `wlc` body verse (`canon_verse>0`) maps to an existing `kjv`
  coordinate — 0 orphans. Spot-check Ps 3 title → `canon_verse=0`, body `wlc 3:2` →
  `canon 3:1`; `wlc` Num 17:1 → `canon 16:36`. Every `krv` verse also maps to a `kjv`
  canon coordinate — 0 orphans (the 4 `KRV_CANON_FIX` spots); the only KJV verses with no
  krv counterpart are the 3 krv merges (1Sa 30:31, Ps 72:20, 2Co 13:12). Spot-check
  `krv` 2Co 13:13 → `canon 13:14` (aligns with KJV 13:14, the grace), Song 6:14 → `canon 6:13`.
- Vectors (if `data/embeddings/` present): `vec_verses` count == 62,203 (31,101 ko +
  31,102 en); a self-KNN of any row returns itself at distance ≈ 0; smoke a real query
  ("the good shepherd" → John 10 / Ps 23, "사랑은 오래 참고" → 1 Cor 13, and a Korean
  query should surface English hits). Without `data/embeddings/`, `build_db.py` skips
  `vec_verses` cleanly (text-only build still valid).

## License

Per-source (PD / CC BY 4.0 / CC BY-SA) — see NOTICE. When adding a text, use only
PD or redistribution-permitted sources, and add its attribution to NOTICE.
