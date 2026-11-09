# Michael · Arabic lessons

Lesson materials for Michael, one page per lesson, listed on the home page by date
(newest first, grouped by month). Every page is self-contained, with its audio inside.

- `index.html`: the home page. Don't edit it by hand: `tools/site.py` writes it.
- `lessons/<date>-<slug>/index.html`: one lesson's page (a grammar lesson, a vocab page,
  homework…).
- `lessons.json`: the list the home page is built from.

To add a lesson page:

```
python3 tools/site.py add path/to/page.html --date 2026-11-16 --slug past-tense \
    --title "The Past Tense · الماضي" --kind Grammar --count "18 slides" \
    --preview "كتبت،رحت،شفت"
```

A vocab page with its `vocab.json` fills in the title, word count and preview words itself:

```
python3 tools/site.py add path/to/vocab-page.html --date 2026-11-16 --slug pp18-19 --vocab vocab.json
```

Then commit and push. Each lesson keeps its own link, so links already sent to Michael keep
working, and adding a page again with the same date and slug replaces it.
