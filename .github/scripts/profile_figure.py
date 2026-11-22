"""Fig. 1 for the profile README, drawn in the style of a journal figure.

Panel a: how the projects fit together (static layout).
Panel b: stars per original repository (live data).
Panel c: releases over time, one tick per tagged release (live data).
"""

from __future__ import annotations

import datetime as dt
import html
import pathlib

SANS = "'Helvetica Neue',Helvetica,Arial,'Liberation Sans',sans-serif"

THEMES = {
    "light": {
        "bg": "#ffffff",
        "ink": "#1a1a1a",
        "grey": "#6e6e6e",
        "rule": "#c9c9c9",
        "faint": "#ececec",
        "accent": "#2f6db5",
        "tint": "#e7eef8",
        "other": "#a3a3a3",
    },
    "dark": {
        "bg": "#0d1117",
        "ink": "#e6edf3",
        "grey": "#8b949e",
        "rule": "#3d444d",
        "faint": "#21262d",
        "accent": "#6ca4f0",
        "tint": "#132339",
        "other": "#5c636b",
    },
}

W = 1200
PANEL_A_H = 300
ROW2_Y = 330
ROW2_H = 400
H = ROW2_Y + ROW2_H

# Panel a: (label, is_this_work, role shown under the box)
CHAIN = (
    ("ChatGPT web", False, ""),
    ("dsh-chatgpt-bridge", True, "steer the session"),
    ("dsh-requirements-alignment", True, "settle decisions first"),
    ("Local agent", False, ""),
    ("PatchWarden", True, "check every patch"),
    ("Merged change", False, ""),
)


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def text(x, y, body, t, size=14, fill=None, weight=400, anchor="start", italic=False):
    style = ' font-style="italic"' if italic else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill or t["ink"]}" font-family="{SANS}" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}"{style}>{esc(body)}</text>'
    )


def arrow(x1, y1, x2, y2, t, color=None):
    color = color or t["ink"]
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="1.2" marker-end="url(#ah)"/>'
    )


def panel_letter(x, y, letter, t):
    return text(x, y, letter, t, size=30, weight=700)


def box(x, y, w, h, label, mine, t):
    fill = t["tint"] if mine else t["bg"]
    stroke = t["accent"] if mine else t["rule"]
    color = t["ink"] if mine else t["grey"]
    weight = 700 if mine else 400
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="3" fill="{fill}" stroke="{stroke}" stroke-width="{1.4 if mine else 1}"/>'
        + text(x + w / 2, y + h / 2 + 6, label, t, size=17, fill=color, weight=weight, anchor="middle")
    )


def panel_a(t) -> str:
    out = [panel_letter(8, 26, "a", t)]
    # legend
    out.append(
        f'<rect x="{W - 250}" y="12" width="14" height="14" rx="2" fill="{t["tint"]}" stroke="{t["accent"]}" stroke-width="1.4"/>'
        + text(W - 228, 25, "this work", t, size=15, fill=t["grey"])
        + f'<rect x="{W - 150}" y="12" width="14" height="14" rx="2" fill="{t["bg"]}" stroke="{t["rule"]}"/>'
        + text(W - 128, 25, "external", t, size=15, fill=t["grey"])
    )
    widths = [max(len(label) * 9.2 + 26, 120) for label, _, _ in CHAIN]
    left, right = 24, W - 8
    gap = (right - left - sum(widths)) / (len(CHAIN) - 1)
    y, bh = 96, 50
    xs = []
    x = left
    for (label, mine, role), bw in zip(CHAIN, widths):
        out.append(box(x, y, bw, bh, label, mine, t))
        if role:
            out.append(text(x + bw / 2, y + bh + 24, role, t, size=15, fill=t["grey"], anchor="middle", italic=True))
        xs.append((x, bw))
        x += bw + gap
    for i in range(len(CHAIN) - 1):
        x1 = xs[i][0] + xs[i][1] + 3
        x2 = xs[i + 1][0] - 3
        out.append(arrow(x1, y + bh / 2, x2, y + bh / 2, t))
    # agentref feeds context into the local agent
    ax, aw = xs[3]
    ref_w = 130
    ref_x = ax + aw / 2 - ref_w / 2
    ref_y = y + bh + 74
    out.append(box(ref_x, ref_y, ref_w, bh, "agentref", True, t))
    out.append(text(ref_x + ref_w / 2, ref_y + bh + 24, "recall past sessions", t, size=15, fill=t["grey"], anchor="middle", italic=True))
    out.append(arrow(ax + aw / 2, ref_y - 4, ax + aw / 2, y + bh + 4, t))
    out.append(text(ax + aw / 2 + 10, (ref_y + y + bh) / 2 + 5, "context", t, size=14, fill=t["grey"], italic=True))
    # feedback loop: failed check goes back to the agent
    px, pw = xs[4]
    loop_y = y - 30
    out.append(
        f'<path d="M{px + pw / 2:.1f} {y - 4} V{loop_y} H{ax + aw / 2:.1f} V{y - 6}" fill="none" stroke="{t["grey"]}" stroke-width="1" stroke-dasharray="4 4" marker-end="url(#ahg)"/>'
        + text((px + pw / 2 + ax + aw / 2) / 2, loop_y - 8, "rejected patches go back", t, size=14, fill=t["grey"], anchor="middle", italic=True)
    )
    return "".join(out)


def axis_ticks_x(x0, x1, y, ticks, t):
    out = [f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{t["ink"]}" stroke-width="1"/>']
    for pos, label in ticks:
        out.append(f'<line x1="{pos:.1f}" y1="{y}" x2="{pos:.1f}" y2="{y + 5}" stroke="{t["ink"]}" stroke-width="1"/>')
        out.append(text(pos, y + 22, label, t, size=14, fill=t["grey"], anchor="middle"))
    return "".join(out)


def panel_b(stars: list[tuple[str, int, bool]], total_projects: int, t) -> str:
    x0, y0 = 0, ROW2_Y
    out = [panel_letter(x0 + 8, y0 + 26, "b", t)]
    out.append(text(x0 + 40, y0 + 26, "Stars per repository", t, size=18, weight=700))
    rows = [row for row in stars if row[1] > 0][:8]
    plot_x, plot_w = x0 + 232, 200
    top = y0 + 50
    row_h = (ROW2_H - 110) / max(len(rows), 1)
    vmax = max([row[1] for row in rows] + [1])
    step = 10 if vmax > 20 else 5
    ceiling = ((vmax + step - 1) // step) * step
    for i in range(0, ceiling + 1, step):
        gx = plot_x + plot_w * i / ceiling
        out.append(f'<line x1="{gx:.1f}" y1="{top - 6}" x2="{gx:.1f}" y2="{top + row_h * len(rows)}" stroke="{t["faint"]}"/>')
    for i, (name, value, mine) in enumerate(rows):
        cy = top + row_h * i + row_h / 2
        bw = plot_w * value / ceiling
        color = t["accent"] if mine else t["other"]
        out.append(text(plot_x - 10, cy + 5, name, t, size=14.5, fill=t["ink"] if mine else t["grey"], anchor="end"))
        out.append(f'<rect x="{plot_x}" y="{cy - row_h * 0.32:.1f}" width="{max(bw, 1.5):.1f}" height="{row_h * 0.64:.1f}" fill="{color}"/>')
        out.append(text(plot_x + bw + 6, cy + 5, str(value), t, size=14, fill=t["grey"]))
    axis_y = top + row_h * len(rows) + 4
    ticks = [(plot_x + plot_w * i / ceiling, str(i)) for i in range(0, ceiling + 1, step)]
    out.append(axis_ticks_x(plot_x, plot_x + plot_w, axis_y, ticks, t))
    out.append(text(plot_x + plot_w / 2, axis_y + 46, f"GitHub stars (n = {total_projects} repositories)", t, size=14.5, fill=t["grey"], anchor="middle"))
    return "".join(out)


def panel_c(releases: list[tuple[str, list[dt.date], bool]], today: dt.date, t) -> str:
    x0, y0 = 486, ROW2_Y
    out = [panel_letter(x0 + 8, y0 + 26, "c", t)]
    total = sum(len(dates) for _, dates, _ in releases)
    out.append(text(x0 + 40, y0 + 26, "Releases over time", t, size=18, weight=700))
    out.append(text(W - 8, y0 + 26, f"{total} tagged releases", t, size=14.5, fill=t["grey"], anchor="end"))
    rows = [row for row in releases if row[1]]
    rows.sort(key=lambda row: min(row[1]))
    start = min(min(dates) for _, dates, _ in rows).replace(day=1)
    end = today
    plot_x, plot_w = x0 + 232, W - 12 - (x0 + 232)
    top = y0 + 50
    row_h = (ROW2_H - 110) / max(len(rows), 1)
    span = max((end - start).days, 1)

    def xpos(day: dt.date) -> float:
        return plot_x + plot_w * (day - start).days / span

    # month gridlines
    month = start
    ticks = []
    while month <= end:
        gx = xpos(month)
        out.append(f'<line x1="{gx:.1f}" y1="{top - 6}" x2="{gx:.1f}" y2="{top + row_h * len(rows)}" stroke="{t["faint"]}"/>')
        ticks.append((gx + plot_w * 15 / span, month.strftime("%b")))
        month = (month.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    ticks = [tick for tick in ticks if tick[0] <= plot_x + plot_w]
    for i, (name, dates, mine) in enumerate(rows):
        cy = top + row_h * i + row_h / 2
        color = t["accent"] if mine else t["other"]
        out.append(text(plot_x - 10, cy + 5, name, t, size=14.5, fill=t["ink"] if mine else t["grey"], anchor="end"))
        out.append(f'<line x1="{plot_x}" y1="{cy:.1f}" x2="{plot_x + plot_w}" y2="{cy:.1f}" stroke="{t["faint"]}" stroke-dasharray="2 3"/>')
        for day in dates:
            gx = xpos(day)
            out.append(f'<line x1="{gx:.1f}" y1="{cy - row_h * 0.3:.1f}" x2="{gx:.1f}" y2="{cy + row_h * 0.3:.1f}" stroke="{color}" stroke-width="2.4"/>')
    axis_y = top + row_h * len(rows) + 4
    out.append(axis_ticks_x(plot_x, plot_x + plot_w, axis_y, ticks, t))
    out.append(text(plot_x + plot_w / 2, axis_y + 46, f"{start.year}, one tick per release", t, size=14.5, fill=t["grey"], anchor="middle"))
    return "".join(out)


def figure(theme: str, stars, total_projects, releases, today) -> str:
    t = THEMES[theme]
    defs = (
        "<defs>"
        f'<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 1 L9 5 L0 9 z" fill="{t["ink"]}"/></marker>'
        f'<marker id="ahg" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 1 L9 5 L0 9 z" fill="{t["grey"]}"/></marker>'
        "</defs>"
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
        'aria-label="Fig. 1: how the projects fit together, stars per repository, and releases over time">'
        f"<title>Fig. 1</title>{defs}"
        f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>'
        + panel_a(t)
        + f'<line x1="0" y1="{ROW2_Y - 14}" x2="{W}" y2="{ROW2_Y - 14}" stroke="{t["faint"]}"/>'
        + panel_b(stars, total_projects, t)
        + panel_c(releases, today, t)
        + "</svg>"
    )


def write_all(out_dir: pathlib.Path, stars, total_projects, releases, today) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for theme in THEMES:
        name = f"fig1-{theme}.svg"
        (out_dir / name).write_text(
            figure(theme, stars, total_projects, releases, today), encoding="utf-8", newline="\n"
        )
        written.append(name)
    return written
