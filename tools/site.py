#!/usr/bin/env python3
"""Michael's lesson site: add a lesson page, rebuild the home page.

  python3 tools/site.py add <page.html> --date 2026-11-09 --slug imperative \
      --title "The Imperative · فعل الأمر" --kind Grammar --count "23 slides" \
      --preview "اكتب،روح،تعا،كول"
  python3 tools/site.py add <vocab-page.html> --date 2026-11-16 --slug pp18-19 --vocab vocab.json
  python3 tools/site.py build

`add` copies a built page (a grammar lesson, a vocab page, homework, anything
self-contained) to lessons/<date>-<slug>/index.html, gives it a link back to the home
page, records it in lessons.json and rebuilds index.html. With --vocab, the title, the
word count and the preview words come from the vocab.json; otherwise give --title,
--count and --preview (Arabic words separated by commas). Adding a page with the same
date and slug again replaces it (same link). `build` only rebuilds index.html.
"""
import argparse
import datetime as dt
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LESSONS = ROOT / "lessons.json"
STUDENT = "Michael"
SUBTITLE = "Arabic lessons · Levantine dialect"

BACK_CSS = (".home-link{display:inline-flex;align-items:center;gap:6px;margin-bottom:4px;font-size:13px;"
            "font-weight:500;color:var(--accent);text-decoration:none}"
            ".home-link:hover{color:var(--accent-ink);text-decoration:underline}")
BACK_LINK = '<a class="home-link" href="../../">&larr; All of %s&rsquo;s lessons</a>' % STUDENT


def load():
    if LESSONS.exists():
        return json.loads(LESSONS.read_text(encoding="utf-8"))
    return {"student": STUDENT, "lessons": []}


def save(data):
    LESSONS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def add_back_link(page):
    if "home-link" in page:
        return page
    page = page.replace('<div class="brand">', '<div class="brand">' + BACK_LINK, 1)
    page = page.replace("</style>", BACK_CSS + "\n</style>", 1)
    if "home-link" not in page:
        sys.exit("couldn't place the back link: the page has no .brand header")
    return page


def cmd_add(a):
    src = pathlib.Path(a.page)
    date = dt.date.fromisoformat(a.date)
    slug = re.sub(r"[^a-z0-9-]+", "-", a.slug.lower()).strip("-")
    folder = "lessons/%s-%s/" % (date.isoformat(), slug)
    out = ROOT / folder / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(add_back_link(src.read_text(encoding="utf-8")), encoding="utf-8")

    if a.vocab:
        vocab = json.loads(pathlib.Path(a.vocab).read_text(encoding="utf-8"))
        rows = [r for s in vocab["sections"] for r in s["rows"]]
        title = a.title or vocab.get("title", slug)
        count = a.count or "%d words" % len(rows)
        preview = [r["ar"] for r in rows]
        kind = a.kind or "Vocabulary"
    else:
        if not (a.title and a.count):
            sys.exit("without --vocab, give --title and --count (and ideally --preview)")
        title, count, kind = a.title, a.count, a.kind or ""
        preview = [w.strip() for w in re.split(r"[,،]", a.preview or "") if w.strip()]
    entry = {
        "date": date.isoformat(),
        "title": title,
        "kind": kind,
        "path": folder,
        "count": count,
        "preview": preview,
    }
    data = load()
    data["lessons"] = [l for l in data["lessons"] if l["path"] != folder] + [entry]
    save(data)
    build()
    print("added", folder, "·", count)


def title_html(t):
    """Escape a title and put any Arabic in it in the Arabic font."""
    return re.sub(r"([\u0600-\u06FF][\u0600-\u06FF\s]*[\u0600-\u06FF]|[\u0600-\u06FF])",
                  r'<bdi class="ar">\1</bdi>', html.escape(t))


def fmt_day(d):
    return d.strftime("%A"), str(d.day), d.strftime("%B %Y")


def build():
    data = load()
    lessons = sorted(data["lessons"], key=lambda l: (l["date"], l["path"]), reverse=True)

    months, out = [], []
    by_date = {}
    for l in lessons:
        by_date.setdefault(l["date"], []).append(l)
    newest = lessons[0] if lessons else None
    for date in sorted(by_date, reverse=True):
        d = dt.date.fromisoformat(date)
        weekday, day, month = fmt_day(d)
        if not months or months[-1] != month:
            if months:
                out.append("</section>")
            months.append(month)
            out.append('<section class="month"><h2>%s</h2>' % html.escape(month))
        cards = []
        for l in by_date[date]:
            prev = l["preview"]
            chips = "".join('<span class="chip ar">%s</span>' % html.escape(w) for w in prev[:6])
            more = '<span class="more">+%d more</span>' % (len(prev) - 6) if len(prev) > 6 else ""
            badge = '<span class="new">Latest</span>' if l is newest else ""
            kind = '<span class="kind">%s</span>' % html.escape(l["kind"]) if l.get("kind") else ""
            cards.append(
                '<a class="card" href="%s">%s'
                '<div class="card-top"><h3>%s</h3>%s<span class="count">%s</span>'
                '<svg class="go" viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></div>'
                '<div class="chips">%s%s</div></a>'
                % (html.escape(l["path"]), kind, title_html(l["title"]), badge, html.escape(l["count"]), chips, more))
        out.append(
            '<div class="day" id="d%s"><div class="date"><span class="dnum">%s</span><span class="wday">%s</span></div>'
            '<div class="cards">%s</div></div>' % (date, day, weekday[:3], "".join(cards)))
    if months:
        out.append("</section>")
    body = "\n".join(out) or '<p class="empty">No lessons yet.</p>'
    meta = "%d lesson%s" % (len(lessons), "" if len(lessons) == 1 else "s")

    page = TEMPLATE.replace("__STUDENT__", html.escape(STUDENT)).replace("__SUB__", html.escape(SUBTITLE))
    page = page.replace("__META__", meta).replace("__BODY__", body)
    (ROOT / "index.html").write_text(page, encoding="utf-8")


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__STUDENT__ · Arabic lessons</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=Scheherazade+New:wght@500;600&display=swap">
<style>
:root{
  --bg:#FAF8F4; --surface:#FFFFFF; --ink:#1F1D1A; --ink-2:#4A463F; --muted:#8B857A;
  --line:#E9E4DB; --line-soft:#F1ECE4;
  --accent:#0F6F5C; --accent-ink:#0B5748; --accent-soft:#E6F1ED;
  --sans:"Instrument Sans", ui-sans-serif, -apple-system, "Segoe UI", Roboto, sans-serif;
  --arabic:"Scheherazade New", "Scheherazade", "Noto Naskh Arabic", "Geeza Pro", "Traditional Arabic", serif;
  --shadow:0 1px 2px rgba(31,29,26,.05), 0 8px 24px -12px rgba(31,29,26,.12);
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:16px;line-height:1.5;-webkit-font-smoothing:antialiased}
.ar{font-family:var(--arabic);direction:rtl;unicode-bidi:isolate;font-weight:600}
header{background:var(--surface);border-bottom:1px solid var(--line)}
.head-in{max-width:760px;margin:0 auto;padding:34px 24px 26px}
h1{margin:0;font-size:30px;font-weight:600;letter-spacing:-.015em;line-height:1.15}
.sub{margin-top:4px;color:var(--ink-2);font-size:15px}
.meta{margin-top:12px;font-size:11px;font-weight:600;letter-spacing:.13em;text-transform:uppercase;color:var(--muted)}
main{max-width:760px;margin:0 auto;padding:28px 24px 80px}
.month{margin-bottom:34px}
.month h2{margin:0 0 14px;font-size:11px;font-weight:600;letter-spacing:.13em;text-transform:uppercase;color:var(--muted)}
.day{display:grid;grid-template-columns:56px 1fr;gap:16px;margin-bottom:14px}
.date{display:flex;flex-direction:column;align-items:center;padding-top:14px}
.dnum{font-size:26px;font-weight:600;line-height:1;font-variant-numeric:tabular-nums}
.wday{margin-top:4px;font-size:11px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.cards{display:flex;flex-direction:column;gap:10px;min-width:0}
.card{display:block;background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px 18px 14px;
  color:inherit;text-decoration:none;box-shadow:var(--shadow);transition:border-color .15s,transform .1s}
.card:hover{border-color:#D5CEC2}
.card:active{transform:scale(.99)}
.card:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.card-top{display:flex;align-items:center;gap:10px}
.card h3{margin:0;font-size:17px;font-weight:600;line-height:1.3}
.card h3 .ar{font-size:1.3em;font-weight:600}
.new{font-size:10.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--accent);background:var(--accent-soft);padding:2px 7px;border-radius:999px}
.kind{display:block;margin-bottom:3px;font-size:11px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
.count{margin-left:auto;font-size:13px;color:var(--muted);white-space:nowrap;font-variant-numeric:tabular-nums}
.go{width:15px;height:15px;color:var(--muted);flex:none}
.card:hover .go{color:var(--accent)}
.chips{display:flex;flex-wrap:wrap;gap:6px 8px;margin-top:10px;direction:rtl;align-items:center}
.chip{font-size:21px;line-height:1.5;padding:0 10px;border-radius:8px;background:var(--line-soft);color:var(--ink-2)}
.more{direction:ltr;font-size:12.5px;color:var(--muted)}
.empty{color:var(--muted)}
@media (max-width:560px){
  .head-in{padding:26px 16px 20px}
  h1{font-size:26px}
  main{padding:22px 16px 60px}
  .day{grid-template-columns:40px 1fr;gap:10px}
  .dnum{font-size:22px}
  .card{padding:14px 14px 12px}
  .chip{font-size:19px;padding:0 8px}
}
</style>
</head>
<body>
<header><div class="head-in">
<h1>__STUDENT__</h1>
<div class="sub">__SUB__</div>
<div class="meta">__META__</div>
</div></header>
<main>
__BODY__
</main>
</body>
</html>
"""


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    pa = sub.add_parser("add")
    pa.add_argument("page")
    pa.add_argument("--date", required=True)
    pa.add_argument("--slug", required=True)
    pa.add_argument("--vocab")
    pa.add_argument("--title")
    pa.add_argument("--kind", help="e.g. Grammar, Vocabulary, Homework")
    pa.add_argument("--count", help='e.g. "23 slides" (taken from --vocab when given)')
    pa.add_argument("--preview", help="Arabic words for the card, separated by commas")
    sub.add_parser("build")
    a = p.parse_args()
    cmd_add(a) if a.cmd == "add" else build()
