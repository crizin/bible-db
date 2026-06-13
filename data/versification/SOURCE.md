# Versification mapping source

`eng.json` — verse-mapping rules between the original-language (Hebrew/Greek,
`org`) versification and the English/Protestant (`eng`, KJV) scheme.

- **Source**: [Copenhagen Alliance versification-specification](https://github.com/Copenhagen-Alliance/versification-specification),
  `versification-mappings/standard-mappings/eng.json`
- **Commit**: `56c093e` (2020-04-02)
- **License**: CC BY-SA 4.0 (data) — see `../../NOTICE`

`mappedVerses` maps `{eng coordinate: org coordinate}`. This dataset's WLC text
follows the `org` scheme, so `scripts/versification.py` inverts the rules to give
each WLC verse a canonical (KJV) coordinate stored in
`verses.canon_chapter` / `verses.canon_verse`. Unmodified verbatim copy.
