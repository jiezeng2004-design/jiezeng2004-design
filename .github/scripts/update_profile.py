#!/usr/bin/env python3
"""Refresh bounded generated sections in the GitHub profile README."""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import pathlib
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

OWNER = os.environ.get("GITHUB_REPOSITORY_OWNER", "jiezeng2004-design")
README_PATH = pathlib.Path(os.environ.get("PROFILE_README_PATH", "README.md"))
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API_ROOT = "https://api.github.com"

PROJECTS = (
    {
        "repo": "relay-forge",
        "name": "RelayForge",
        "category": "LOCAL GATEWAY",
        "description_zh": "本地优先的 AI 编程网关：组合路由、回退、隐私日志，兼容 OpenAI/Anthropic 接口。",
        "description_en": "Local-first AI coding gateway with combo routing, fallback, privacy logs, and OpenAI/Anthropic compatibility.",
        "tech": ("JavaScript", "Gateway", "Local-first"),
    },
    {
        "repo": "CodexJournal-Lite",
        "name": "CodexJournal-Lite",
        "category": "WORK MEMORY",
        "description_zh": "把本地 Codex 会话归档为可检索的私有工作记忆与仪表盘。",
        "description_en": "Turn local Codex sessions into a searchable private work memory and dashboard.",
        "tech": ("JavaScript", "Codex", "Local-first"),
    },
    {
        "repo": "ProbeMux",
        "name": "ProbeMux",
        "category": "MODEL PROBING",
        "description_zh": "一次探测，处处配置：以证据为先探测模型能力，并生成各编程 Agent 的配置。",
        "description_en": "Probe once, configure everywhere: evidence-first model capability probing for coding agents.",
        "tech": ("TypeScript", "CLI", "LLM"),
    },
    {
        "repo": "XJTU-Codex-Theme",
        "name": "XJTU-Codex-Theme",
        "category": "DESKTOP THEME",
        "description_zh": "面向 Codex Desktop 的免重启主题，含 XJTU 预设与自定义模板。",
        "description_en": "No-restart themes for Codex Desktop, with an XJTU preset and a custom template.",
        "tech": ("JavaScript", "Electron", "Theme"),
    },
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


def latest_releases() -> dict[str, dict]:
    result: dict[str, dict] = {}
    for project in PROJECTS:
        repo = urllib.parse.quote(project["repo"])
        release = api_get(f"/repos/{urllib.parse.quote(OWNER)}/{repo}/releases/latest")
        result[project["repo"]] = {
            "tag": str(release["tag_name"]),
            "url": str(release["html_url"]),
        }
    return result


def project_cell(project: dict, release: dict, language: str) -> list[str]:
    repo = html.escape(project["repo"])
    name = html.escape(project["name"])
    tag = html.escape(release["tag"])
    release_url = html.escape(release["url"], quote=True)
    repo_url = f"https://github.com/{html.escape(OWNER)}/{repo}"
    description = html.escape(project[f"description_{language}"])
    tech = " ".join(f"<code>{html.escape(item)}</code>" for item in project["tech"])
    link_label = "仓库" if language == "zh" else "Repository"
    return [
        '    <td width="50%" valign="top">',
        f"      <code>{html.escape(project['category'])} / {tag}</code>",
        f'      <p><strong><a href="{repo_url}">{name} &rarr;</a></strong></p>',
        f"      <p>{description}</p>",
        f"      <p>{tech}</p>",
        f'      <p><a href="{repo_url}">{link_label}</a> &middot; <a href="{release_url}">{tag}</a></p>',
        "    </td>",
    ]


def render_latest(releases: dict[str, dict], language: str) -> str:
    heading = (
        "### `// 更多项目`"
        if language == "zh"
        else "### `// MORE_PROJECTS` - Also shipped"
    )
    lines = [heading, "", "<table>"]
    for index in range(0, len(PROJECTS), 2):
        lines.append("  <tr>")
        for project in PROJECTS[index : index + 2]:
            lines.extend(project_cell(project, releases[project["repo"]], language))
        lines.append("  </tr>")
    lines.append("</table>")
    return "\n".join(lines)


def merged_upstream_prs() -> int:
    query = urllib.parse.quote(f"author:{OWNER} type:pr is:merged -user:{OWNER}")
    return int(api_get(f"/search/issues?q={query}&per_page=1")["total_count"])


def render_snapshot(repositories: list[dict], merged_prs: int, language: str) -> str:
    originals = [
        repo
        for repo in repositories
        if not repo.get("fork") and not repo.get("archived") and repo["name"] != OWNER
    ]
    original_count = len(originals)
    stars = sum(int(repo.get("stargazers_count", 0)) for repo in originals)
    forks = sum(int(repo.get("forks_count", 0)) for repo in originals)
    snapshot_date = dt.datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()

    if language == "zh":
        heading = "### `// GitHub 快照`"
        labels = ("原创项目", "累计 Stars", "累计 Forks", "合并到上游的 PR")
        note = f"每周自动更新 · {snapshot_date} · 仅统计未归档原创仓库"
    else:
        heading = "### `// GITHUB_SNAPSHOT` - Public profile data"
        labels = (
            "Original projects",
            "Total stars",
            "Total forks",
            "PRs merged upstream",
        )
        note = (
            f"Refreshed weekly · {snapshot_date} · "
            "non-archived original repositories only"
        )

    values = (original_count, stars, forks, merged_prs)
    lines = [heading, "", "<table>", "  <tr>"]
    for value, label in zip(values, labels, strict=True):
        lines.append(
            f'    <td align="center"><strong>{value}</strong><br /><sub>{label}</sub></td>'
        )
    lines.extend(
        [
            "  </tr>",
            "</table>",
            "",
            f'<p align="center"><sub>{note}</sub></p>',
        ]
    )
    return "\n".join(lines)


def replace_block(text: str, key: str, body: str) -> str:
    start_marker = f"<!-- profile:auto:{key}:start -->"
    end_marker = f"<!-- profile:auto:{key}:end -->"
    if text.count(start_marker) != 1 or text.count(end_marker) != 1:
        raise RuntimeError(f"Expected exactly one marker pair for {key}")
    start = text.index(start_marker) + len(start_marker)
    end = text.index(end_marker, start)
    return text[:start] + "\n" + body.rstrip() + "\n" + text[end:]


def main() -> None:
    repositories = list_owner_repositories()
    releases = latest_releases()
    merged_prs = merged_upstream_prs()

    original = README_PATH.read_text(encoding="utf-8")
    updated = original
    updated = replace_block(updated, "latest-zh", render_latest(releases, "zh"))
    updated = replace_block(updated, "snapshot-zh", render_snapshot(repositories, merged_prs, "zh"))
    updated = replace_block(updated, "latest-en", render_latest(releases, "en"))
    updated = replace_block(updated, "snapshot-en", render_snapshot(repositories, merged_prs, "en"))

    if updated != original:
        README_PATH.write_text(updated, encoding="utf-8", newline="\n")
        print("README generated sections refreshed.")
    else:
        print("README generated sections already current.")


if __name__ == "__main__":
    main()
