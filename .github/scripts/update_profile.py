#!/usr/bin/env python3
"""Refresh the generated parts of the GitHub profile: Fig. 1 and the numbers around it."""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import profile_figure  # noqa: E402

OWNER = os.environ.get("GITHUB_REPOSITORY_OWNER", "jiezeng2004-design")
README_PATH = pathlib.Path(os.environ.get("PROFILE_README_PATH", "README.md"))
ASSETS_DIR = README_PATH.parent / "assets"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API_ROOT = "https://api.github.com"

# (repo, what it does, shown as "this work" in Fig. 1a)
PROJECTS = (
    ("dsh-chatgpt-bridge", "Steer local agent sessions from ChatGPT.", True),
    ("dsh-requirements-alignment", "Settle key decisions before any code.", True),
    ("PatchWarden", "Check every patch before it lands.", True),
    ("agentref", "Read-only recall of past agent sessions.", True),
    ("relay-forge", "Local gateway with provider fallback.", False),
    ("CodexJournal-Lite", "Searchable archive of Codex sessions.", False),
    ("ProbeMux", "Probe a model once, configure every agent.", False),
    ("XJTU-Codex-Theme", "No-restart themes for Codex Desktop.", False),
)


def api_get(path: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-readme-refresh",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    request = urllib.request.Request(f"{API_ROOT}{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def list_owner_repositories() -> list[dict]:
    repositories: list[dict] = []
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {"per_page": 100, "page": page, "type": "owner", "sort": "full_name"}
        )
        batch = api_get(f"/users/{urllib.parse.quote(OWNER)}/repos?{query}")
        repositories.extend(batch)
        if len(batch) < 100:
            return repositories
        page += 1


def list_releases(repo: str) -> list[dict]:
    path = f"/repos/{urllib.parse.quote(OWNER)}/{urllib.parse.quote(repo)}/releases?per_page=100"
    try:
        releases = api_get(path)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return []
        raise
    return [r for r in releases if not r.get("draft") and r.get("published_at")]


def merged_upstream_prs() -> int:
    query = urllib.parse.quote(f"author:{OWNER} type:pr is:merged -user:{OWNER}")
    return int(api_get(f"/search/issues?q={query}&per_page=1")["total_count"])


def parse_day(stamp: str) -> dt.date:
    return dt.date.fromisoformat(stamp[:10])


def render_caption(n_starred: int, n_original: int, n_releases: int, first: dt.date, today: dt.date) -> str:
    period = f"{first.strftime('%B')}–{today.strftime('%B %Y')}"
    return (
        "**Fig. 1 | How the projects fit together.** "
        "**a**, An agent run from request to merged change. Blue boxes are my projects; grey boxes are "
        "the tools they connect. A patch that fails PatchWarden's checks goes back to the agent instead of landing. "
        f"**b**, Stars per repository, for the {n_starred} of my {n_original} original repositories that have any. "
        f"**c**, Every tagged release of the eight projects in Table 1, {period} ({n_releases} in total)."
    )


def render_table(repos: dict, releases: dict) -> str:
    lines = [
        "<table>",
        "  <tr><th>Project</th><th>What it does</th><th>Stars</th><th>Latest release</th></tr>",
    ]
    for repo, description, _ in PROJECTS:
        url = f"https://github.com/{html.escape(OWNER)}/{html.escape(repo)}"
        stars = int(repos.get(repo, {}).get("stargazers_count", 0))
        items = releases.get(repo, [])
        if items:
            latest = max(items, key=lambda r: r["published_at"])
            latest_cell = f'<a href="{html.escape(latest["html_url"], quote=True)}">{html.escape(latest["tag_name"])}</a>'
        else:
            latest_cell = "&mdash;"
        lines.extend(
            [
                "  <tr>",
                f'    <td><a href="{url}"><b>{html.escape(repo)}</b></a></td>',
                f"    <td>{html.escape(description)}</td>",
                f'    <td align="right">{stars}</td>',
                f"    <td>{latest_cell}</td>",
                "  </tr>",
            ]
        )
    lines.append("</table>")
    return "\n".join(lines)


def render_upstream_caption(merged_prs: int) -> str:
    return (
        f"**Table 2 | Changes merged into other projects.** "
        f"Selected pull requests; {merged_prs} of mine have been merged into repositories I don't own."
    )


def replace_block(text: str, key: str, body: str) -> str:
    start_marker = f"<!-- profile:auto:{key}:start -->"
    end_marker = f"<!-- profile:auto:{key}:end -->"
    if text.count(start_marker) != 1 or text.count(end_marker) != 1:
        raise RuntimeError(f"Expected exactly one marker pair for {key}")
    start = text.index(start_marker) + len(start_marker)
    end = text.index(end_marker, start)
    return text[:start] + "\n" + body.rstrip() + "\n" + text[end:]


def main() -> None:
    today = dt.datetime.now(ZoneInfo("Asia/Shanghai")).date()
    repositories = list_owner_repositories()
    by_name = {repo["name"]: repo for repo in repositories}
    originals = [
        repo
        for repo in repositories
        if not repo.get("fork") and not repo.get("archived") and repo["name"] != OWNER
    ]
    featured = {repo for repo, _, mine in PROJECTS if mine}
    stars = sorted(
        (
            (repo["name"], int(repo.get("stargazers_count", 0)), repo["name"] in featured)
            for repo in originals
        ),
        key=lambda row: (-row[1], row[0].lower()),
    )
    releases = {repo: list_releases(repo) for repo, _, _ in PROJECTS}
    release_rows = [
        (repo, [parse_day(r["published_at"]) for r in releases[repo]], mine)
        for repo, _, mine in PROJECTS
    ]
    all_days = [day for _, days, _ in release_rows for day in days]

    written = profile_figure.write_all(ASSETS_DIR, stars, len(originals), release_rows, today)
    print(f"Figure written: {', '.join(written)}")

    original = README_PATH.read_text(encoding="utf-8")
    updated = original
    updated = replace_block(
        updated,
        "fig1-caption",
        render_caption(
            sum(1 for row in stars if row[1] > 0), len(originals), len(all_days), min(all_days), today
        ),
    )
    updated = replace_block(updated, "table1", render_table(by_name, releases))
    updated = replace_block(updated, "table2-caption", render_upstream_caption(merged_upstream_prs()))
    if updated != original:
        README_PATH.write_text(updated, encoding="utf-8", newline="\n")
        print("README refreshed.")
    else:
        print("README already current.")


if __name__ == "__main__":
    main()
