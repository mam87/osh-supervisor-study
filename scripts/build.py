#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build script: parses the 18 source safety-unitN.html slide decks and produces
structured JSON data consumed by the static study site (index.html / unit.html /
quiz.html / numbers.html / glossary.html).

Source of truth: /mnt/user-data/outputs/safety-unit{1..18}.html
Output: data/unit-{n}.json (per-unit slides), data/catalog.json (unit metadata),
        data/questions.json (aggregated question bank), data/numbers.json
        (aggregated key-numbers tables), data/search-index.json (flat search index).
"""
import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

SRC_DIR = Path("/mnt/user-data/outputs")
OUT_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR.mkdir(exist_ok=True)

N_UNITS = 18

# Manually curated per-unit metadata not reliably derivable from the HTML alone.
ICONS = {
    1: "shield-check", 2: "hard-hat", 3: "flame", 4: "zap", 5: "wind",
    6: "ear", 7: "stethoscope", 8: "bar-chart-3", 9: "hammer",
    10: "flame-kindling", 11: "package-open", 12: "boxes",
    13: "activity", 14: "presentation", 15: "package",
    16: "graduation-cap", 17: "search", 18: "file-text",
}

PAGE_RANGES = {
    1: "—", 2: "—", 3: "—", 4: "—", 5: "—", 6: "—", 7: "—", 8: "—", 9: "—",
    10: "—", 11: "—", 12: "—",
    13: "٥٦٤–٦٠٠", 14: "٦٠١–٦٥٠", 15: "٧٤٥–٧٩٦", 16: "٦٥١–٦٨٢",
    17: "٦٨٤–٧٢٤", 18: "٧٩٧–٨٢٤",
}

def slide_type(section):
    cls = section.get("class", [])
    if "cover" in cls:
        return "cover"
    if "divider" in cls:
        return "divider"
    if "review-cover" in cls:
        return "review-cover"
    return "content"

def text_of(el):
    if el is None:
        return ""
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()

def extract_colors(soup):
    style = soup.find("style")
    css = style.get_text() if style else ""
    colors = {}
    for var in ("navy", "amber", "amber-deep"):
        m = re.search(r"--%s:\s*(#[0-9A-Fa-f]{3,6})" % var, css)
        if m:
            colors[var] = m.group(1)
    return colors

def clean_body_html(inner, eyebrow_el, heading_el):
    """Return the slide-inner HTML with the eyebrow/heading tags stripped
    (the site renders those separately), keeping all other markup
    (cards, tables, lists, details.q, formula-box, etc.) verbatim so the
    shared site stylesheet renders them identically to the source decks."""
    frag = BeautifulSoup(str(inner), "html.parser")
    for tag_name, ref in (("div", eyebrow_el), ("h1", None), ("h2", None)):
        pass
    # remove the first .eyebrow, and the first h1/h2 (title) - by exact match
    ev = frag.select_one(".eyebrow")
    if ev:
        ev.decompose()
    h = frag.select_one("h1, h2")
    if h:
        h.decompose()
    return frag.decode_contents().strip()

def parse_unit(n):
    path = SRC_DIR / f"safety-unit{n}.html"
    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    colors = extract_colors(soup)
    sections = soup.select("main#deck > section.slide")

    slides = []
    for idx, sec in enumerate(sections):
        inner = sec.select_one(".slide-inner") or sec
        eyebrow_el = inner.select_one(".eyebrow")
        heading_el = inner.select_one("h1, h2")
        eyebrow = text_of(eyebrow_el)
        heading = text_of(heading_el)
        body_html = clean_body_html(inner, eyebrow_el, heading_el)
        plain_text = text_of(inner)
        questions = []
        for q in inner.select("details.q"):
            summary = text_of(q.select_one("summary"))
            opts = [text_of(o) for o in q.select(".qopts div")]
            answer = text_of(q.select_one(".answer"))
            questions.append({"q": summary, "options": opts, "answer": answer})
        num_rows = []
        for tbl in inner.select("table.num-table"):
            for tr in tbl.select("tr"):
                cells = [text_of(td) for td in tr.select("td")]
                if len(cells) == 2:
                    num_rows.append(cells)

        slides.append({
            "i": idx,
            "type": slide_type(sec),
            "eyebrow": eyebrow,
            "heading": heading,
            "html": body_html,
            "text": plain_text,
            "questions": questions,
            "numbers": num_rows,
        })

    cover = next((s for s in slides if s["type"] == "cover"), slides[0])
    title = cover["heading"] or f"الوحدة {n}"
    desc_el = soup.select_one("section.cover .slide-inner > p")
    description = text_of(desc_el)
    meta_el = soup.select_one("section.cover .meta")
    meta = text_of(meta_el)

    unit = {
        "n": n,
        "title": title,
        "description": description,
        "meta": meta,
        "colors": colors,
        "icon": ICONS.get(n, "book-open"),
        "pages": PAGE_RANGES.get(n, "—"),
        "slideCount": len(slides),
        "slides": slides,
    }
    return unit

def main():
    catalog = []
    all_questions = []
    all_numbers = []
    search_index = []

    for n in range(1, N_UNITS + 1):
        print(f"parsing unit {n}...", file=sys.stderr)
        unit = parse_unit(n)

        catalog.append({
            "n": unit["n"], "title": unit["title"], "description": unit["description"],
            "colors": unit["colors"], "icon": unit["icon"], "pages": unit["pages"],
            "slideCount": unit["slideCount"],
        })

        (OUT_DIR / f"unit-{n}.json").write_text(
            json.dumps(unit, ensure_ascii=False), encoding="utf-8"
        )

        for s in unit["slides"]:
            if s["questions"]:
                for qi, q in enumerate(s["questions"]):
                    is_tf = "answer" in q and (q["answer"].startswith("صح") or q["answer"].startswith("خطأ"))
                    all_questions.append({
                        "unit": n, "unitTitle": unit["title"],
                        "slide": s["i"], "qi": qi,
                        "type": "tf" if is_tf else "mcq",
                        "q": q["q"], "options": q["options"], "answer": q["answer"],
                    })
            if s["numbers"] and ("الأرقام" in s["eyebrow"] or "القيم" in s["eyebrow"]):
                for row in s["numbers"]:
                    all_numbers.append({"unit": n, "unitTitle": unit["title"], "topic": row[0], "value": row[1]})
            if s["text"]:
                search_index.append({
                    "unit": n, "unitTitle": unit["title"], "slide": s["i"],
                    "type": s["type"], "eyebrow": s["eyebrow"], "heading": s["heading"],
                    "text": s["text"][:600],
                })

    (OUT_DIR / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "questions.json").write_text(json.dumps(all_questions, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "numbers.json").write_text(json.dumps(all_numbers, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "search-index.json").write_text(json.dumps(search_index, ensure_ascii=False), encoding="utf-8")

    print(f"Done. {len(catalog)} units, {len(all_questions)} questions, "
          f"{len(all_numbers)} number rows, {len(search_index)} search entries.", file=sys.stderr)

if __name__ == "__main__":
    main()
