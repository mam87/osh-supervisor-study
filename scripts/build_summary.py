#!/usr/bin/env python3
"""Build summary.html from content/summary-*.md.

Usage:  pip install markdown && python3 scripts/build_summary.py
Edit the Markdown files in content/, then re-run this script.
```latex blocks are rendered in the browser by KaTeX.
"""
import html
import re
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
TABS = [
    ("books", "كتب المعهد", ROOT / "content" / "summary-books.md"),
    ("law", "التشريعات والضمان", ROOT / "content" / "summary-legislation.md"),
]


def slugify(text, used):
    base = re.sub(r"[^\w؀-ۿ]+", "-", text).strip("-")[:48] or "s"
    slug, i = base, 2
    while slug in used:
        slug, i = f"{base}-{i}", i + 1
    used.add(slug)
    return slug


def render(md_text, prefix):
    # protect latex blocks before markdown processing
    maths = []

    def keep(m):
        maths.append(m.group(1).strip())
        return f"\n\nMATHBLOCK{len(maths) - 1}X\n\n"

    md_text = re.sub(r"```latex\n(.*?)```", keep, md_text, flags=re.S)
    # drop the H1 (shown in page header)
    md_text = re.sub(r"\A# .*\n", "", md_text)
    body = markdown.markdown(md_text, extensions=["tables", "fenced_code", "sane_lists"])

    for i, tex in enumerate(maths):
        block = f'<div class="math-block" dir="ltr">$${html.escape(tex)}$$</div>'
        body = body.replace(f"<p>MATHBLOCK{i}X</p>", block)

    used, toc = set(), []

    def add_id(m):
        level, inner = m.group(1), m.group(2)
        plain = re.sub(r"<[^>]+>", "", inner)
        sid = prefix + "-" + slugify(plain, used)
        if level == "2":
            toc.append((sid, plain))
        return f'<h{level} id="{sid}">{inner}</h{level}>'

    body = re.sub(r"<h([23])>(.*?)</h\1>", add_id, body)
    body = body.replace("<table>", '<div class="tbl-wrap"><table>').replace("</table>", "</table></div>")
    return body, toc


def main():
    panels, tabs_html = [], []
    for idx, (key, label, path) in enumerate(TABS):
        body, toc = render(path.read_text(encoding="utf-8"), key)
        toc_html = "".join(f'<a href="#{sid}">{html.escape(t)}</a>' for sid, t in toc)
        active = " active" if idx == 0 else ""
        tabs_html.append(
            f'<button class="sum-tab{active}" data-tab="{key}" role="tab">{label}</button>')
        panels.append(
            f'<section class="sum-panel{active}" id="panel-{key}" role="tabpanel">'
            f'<nav class="jump-nav">{toc_html}</nav><article class="sum-body">{body}</article></section>')

    tpl = (ROOT / "scripts" / "summary_template.html").read_text(encoding="utf-8")
    out = tpl.replace("{{TABS}}", "\n".join(tabs_html)).replace("{{PANELS}}", "\n".join(panels))
    (ROOT / "summary.html").write_text(out, encoding="utf-8")
    print("summary.html written")


if __name__ == "__main__":
    main()
