# NOTICE — 데이터 출처 및 라이선스

이 저장소는 여러 출처의 데이터를 통합하며, 각 데이터는 고유한 라이선스를 따른다.
재배포·활용 시 아래 출처 표기(attribution)를 준수할 것.

## 코드 (`scripts/`)
MIT License — `LICENSE` 참조.

## 성경 본문 및 어휘 데이터 (`data/`)

### 개역한글판 (Korean Revised Version, 1961) — `data/krv/`
- 라이선스: **Public Domain** (저작재산권 보호기간 만료, 2012~)
- 출처: 재단법인 대한성서공회 (Korean Bible Society)
- 인격권(동일성유지권·성명표시권) 준수: 본문을 임의로 변경하지 말 것. 출처를
  "성경전서 개역한글판 (대한성서공회)"로 표기할 것.
- 수집처: holybible.or.kr (정본), bible.bskorea.or.kr (대조)

### King James Version (1769) — `data/kjv/`
- 라이선스: **Public Domain** (미국 기준)
- 출처: scrollmapper/bible_databases (원천: CrossWire KJV2006 OSIS / eBible.org)
- ⚠️ 영국 내에서는 Crown copyright(Cambridge University Press). 영국 외 지역은 PD.

### 히브리어 Westminster Leningrad Codex — `data/hebrew/`
- 본문(자음·모음·악센트): **Public Domain** (Leningrad Codex 기반)
- 형태소·Strong 태깅: **CC BY 4.0** — Open Scriptures Hebrew Bible
- 출처: openscriptures/morphhb
- 귀속 표기: "Open Scriptures Hebrew Bible (https://github.com/openscriptures/morphhb)"

### 그리스어 Byzantine Majority Text (Robinson-Pierpont 2018) — `data/greek/byz*`
- 라이선스: **Public Domain** (Unlicense)
- 출처: byztxt/byzantine-majority-text (Maurice A. Robinson & William G. Pierpont)

### Strong's Hebrew & Greek Dictionaries — `data/strongs/`
- 원본: **Public Domain** (James Strong, 1890)
- 디지털 가공본: **CC BY-SA** — openscriptures/strongs
- 귀속 + 동일조건변경허락(ShareAlike) 준수.

### Versification 매핑 (원어↔KJV) — `data/versification/`
- 라이선스: **CC BY-SA 4.0** — Copenhagen Alliance for Open Biblical Language Resources
- 출처: Copenhagen-Alliance/versification-specification (`eng.json`, commit 56c093e)
- 원어(히브리/그리스)↔KJV 절 매핑 룰. WLC 절에 canonical(KJV) 좌표(`verses.canon_*`)를
  부여하는 데 사용. `eng.json`은 verbatim 보존.
- 귀속 + 동일조건변경허락(ShareAlike) 준수.

### 의미 카테고리 (Semantic Categories) — `data/categories/`
- 라이선스: **CC BY 4.0**
- 본 프로젝트가 LLM으로 생성. 각 Strong 번호를 `taxonomy.md`의 18개 의미 도메인
  체계로 분류한 데이터(`strong_categories.jsonl`).
- 귀속 표기: "bible-db semantic categories"

### 의미 벡터 색인 (Semantic Vector Index) — `data/embeddings/`
- 라이선스: **CC BY 4.0** (본 프로젝트가 산출한 벡터)
- 한국어(개역한글)·영어(KJV) 절 본문을 **Google Gemini Embedding 2**로 임베딩한 768차원
  int8 벡터(`verses.gemini2-768.int8.npy` + `verses.meta.jsonl`). `build_db.py`가
  `bible.sqlite`의 sqlite-vec `vec0` 테이블(`vec_verses`)로 통합한다.
- 임베딩 모델: Google Gemini Embedding 2 (Google LLC). Gemini API 약관에 따라 생성된
  출력물이며, 모델 가중치가 아니라 본문의 벡터 표현만 배포한다. 본문 자체는 위
  개역한글/KJV 항목의 라이선스를 그대로 따른다(벡터는 derived 표현).
- 귀속 표기: "bible-db semantic vectors (Gemini Embedding 2)"

## 포함하지 않은 데이터

### STEPBible TAGNT (그리스어 7판본 비교)
- 라이선스: CC BY 4.0 이나, STEPBible 측이 "데이터를 직접 재배포하지 말고
  github.com/STEPBible 를 출처로 안내"할 것을 권고한다.
- 이 권고를 존중하여 가공 데이터(`tagnt_words.jsonl`)를 저장소에 **포함하지 않는다**.
- 필요하면: STEPBible-Data 저장소에서 TAGNT 파일을 받아 `scripts/parse_tagnt.py`
  를 직접 실행하여 생성할 것. (Tyndale House Cambridge / STEPBible.org, CC BY 4.0)
