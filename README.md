# Kosovo — legislation as Markdown (LawCodex)

Laws of the **Republic of Kosovo** (Republika e Kosovës / Republika Kosovo) as plain Markdown,
generated from the **Gazeta Zyrtare e Republikës së Kosovës** (Official Gazette, Office of the
Prime Minister, https://gzk.rks-gov.net), in its three publication languages:

| Directory | Language | Constitution | Codes | Laws |
|---|---|---|---|---|
| `sq/` (`kushtetuta/`, `kode/`, `ligje/<year>/`) | Albanian (official) | 1 | 5 | 607 |
| `sr/` (`ustav/`, `zakonici/`, `zakoni/<year>/`) | Serbian (official) | 1 | 6 | 612 |
| `en/` (`constitution/`, `codes/`, `laws/<year>/`) | English (translation published by the Gazette) | 1 | 6 | 610 |

Part of [LawCodex](https://github.com/LawCodex): one repository per jurisdiction.

## Selection and versions

- The set of acts is the Gazette's official **"Lista e Ligjeve"** (LawInForceList.aspx), the
  list of laws in force (622 laws and codes), plus the Constitution. Small differences between
  languages are acts whose text is missing in one language.
- For 147 laws and codes, and for the Constitution, the Gazette publishes a **consolidated text**
  ("Aktet e konsoliduara", 2024–2026). Those files use it (`text_version: consolidated`,
  `base_act` = the original act). The Gazette states that these consolidated texts are **not
  the official version** ("Teksti i spastruar i ligjit nuk paraqet version zyrtar").
- Otherwise the text is the act as originally published (`text_version: original`); where the
  Gazette lists later amending acts, a `note` says so — amending laws that are themselves in the
  list of laws in force have their own files.
- Text comes from the Gazette's HTML text view, or, for recent acts and consolidated texts, from
  the PDF the site provides (`pdftotext`). Article labels (Neni / Član / Article) are `####`
  headings; all-caps divisions `###`; running page headers were removed.

File names: `<year>-<act number>-<slug>.md` (year of publication), e.g.
`sq/ligje/2013/2013-04-l-193-per-avokatine.md`. Front matter: `title`, `identifier` (act
number), `type`, `date` (publication), `last_amended` (publication of the consolidated text),
`status`, `text_version`, `gazette`, `source`, `base_act`, `retrieved`.

## What is NOT covered

- Bosnian and Turkish versions (the site has them for some acts), sub-legal acts
  (regulations, administrative instructions), municipal acts, Constitutional Court decisions,
  international agreements as such, and repealed laws.
- UNMIK regulations still applicable are only included where they appear in the list of laws.

## Licence

Kosovo copyright law excludes official texts of a legislative, administrative or judicial nature
from protection. Texts reproduced as published by the Official Gazette.

## Regenerating

```
python scripts/xk_fetch.py  ../_raw/xk      # lists + texts in sq, sr, en
python scripts/xk_convert.py ../_raw/xk .
```

Needs `pdftotext` (poppler) and `scripts/requirements.txt`. Retrieved 2026-10-12.
