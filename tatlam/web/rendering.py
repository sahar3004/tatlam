from __future__ import annotations

import json
from typing import Any

from flask import render_template, render_template_string
from jinja2 import TemplateNotFound


def render_with_fallback(template_name: str, **ctx: Any) -> str:
    """Render a template or fallback to minimal HTML snippets.

    Parameters
    ----------
    template_name : str
        Jinja template name expected to exist in templates/.
    **ctx : Any
        Context variables for rendering.

    Returns
    -------
    str
        HTML string. If the template is missing, returns a compact HTML fallback.
    """
    try:
        return render_template(template_name, **ctx)
    except TemplateNotFound:
        if template_name == "home.html":
            cats = ctx.get("cats", [])
            html = ["<h1>קטגוריות</h1>", "<ul>"]
            for c in cats:
                html.append(
                    f"<li><a href='/cat/{c['slug']}'>{c['title']}</a> – {c['count']} תטל\"מים</li>"
                )
            html.append("</ul>")
            return "\n".join(html)
        if template_name == "list.html":
            items = ctx.get("items", [])
            title = ctx.get("cat_title", "קטגוריה")
            html = [f"<h1>{title}</h1>", "<ul>"]
            for s in items:
                part1 = (
                    f"<li><a href='/scenario/{s.get('id','')}'>{s.get('title','(ללא כותרת)')}</a>"
                )
                cat = s.get("category", "")
                tl = s.get("threat_level", "?")
                lk = s.get("likelihood", "?")
                cx = s.get("complexity", "?")
                part2 = f" – {cat} | {tl}/{lk}/{cx}</li>"
                html.append(part1 + part2)
            html.append("</ul>")
            return "\n".join(html)
        if template_name == "detail.html":
            s = ctx.get("s", {})

            def li_list(key: str) -> str:
                val = s.get(key) or []
                out: list[str] = []
                for x in val:
                    if isinstance(x, (dict, list)):
                        content = json.dumps(x, ensure_ascii=False)
                    else:
                        content = x
                    out.append(f"<li>{content}</li>")
                return "".join(out)

            html = [
                f"<h2>{s.get('title','(ללא כותרת)')}</h2>",
                f"<p><b>קטגוריה:</b> {s.get('category','')}</p>",
                f"<p><b>מיקום:</b> {s.get('location','')}</p>",
                f"<p><b>רקע:</b> {s.get('background','')}</p>",
                "<h3>🧭 שלבים</h3>",
                f"<ol>{li_list('steps')}</ol>",
                "<h3>📢 הנחיות תגובה</h3>",
                f"<ul>{li_list('required_response')}</ul>",
                "<h3>📝 תחקור</h3>",
                f"<ul>{li_list('debrief_points')}</ul>",
            ]
            return "\n".join(html)
        return render_template_string("<pre>{{ ctx | tojson(indent=2) }}</pre>", ctx=ctx)


__all__ = ["render_with_fallback"]
