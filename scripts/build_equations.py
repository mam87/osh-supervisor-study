#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract all .formula-box entries across unit-*.json into data/equations.json."""
import json
from pathlib import Path
from bs4 import BeautifulSoup

DATA = Path(__file__).resolve().parent.parent / "data"

# Manual fixes for formula-boxes whose equation lives in prose rather than a .feq div.
MANUAL_EQUATIONS = {
    ("أ — معدّل تكرار الحوادث (Frequency Rate)",): "معدّل التكرار = (عدد الإصابات المسبِّبة للتغيّب عن العمل × ١٬٠٠٠٬٠٠٠) ÷ عدد ساعات العمل الفعلية لكافّة العاملين",
    ("ب — معدّل شدّة الحوادث (Severity Rate)",): "معدّل الشدّة = (عدد أيّام التغيّب الناتجة عن الإصابات × ١٬٠٠٠٬٠٠٠) ÷ عدد ساعات العمل الفعلية لكافّة العاملين",
}

def main():
    out = []
    for n in range(1, 19):
        p = DATA / f"unit-{n}.json"
        if not p.exists():
            continue
        unit = json.loads(p.read_text(encoding="utf-8"))
        for s in unit["slides"]:
            if "formula-box" not in s["html"]:
                continue
            frag = BeautifulSoup(s["html"], "html.parser")
            for fb in frag.select(".formula-box"):
                fname_el = fb.select_one(".fname")
                feq_el = fb.select_one(".feq")
                err_el = fb.select_one(".err")
                name = fname_el.get_text(" ", strip=True) if fname_el else ""
                eq = feq_el.get_text(" ", strip=True) if feq_el else ""
                if not eq:
                    eq = MANUAL_EQUATIONS.get((name,), "")
                desc_parts = []
                for p_el in fb.find_all("p"):
                    if err_el and p_el in err_el.find_all("p"):
                        continue
                    desc_parts.append(p_el.get_text(" ", strip=True))
                out.append({
                    "unit": n,
                    "unitTitle": unit["title"],
                    "slideId": s["i"],
                    "section": s["eyebrow"],
                    "topic": s["heading"],
                    "name": name,
                    "equation": eq,
                    "desc": " — ".join([d for d in desc_parts if d]),
                    "note": err_el.get_text(" ", strip=True) if err_el else "",
                })
    (DATA / "equations.json").write_text(json.dumps(out, ensure_ascii=False, indent=None), encoding="utf-8")
    print(f"Wrote {len(out)} equations to data/equations.json")

if __name__ == "__main__":
    main()
