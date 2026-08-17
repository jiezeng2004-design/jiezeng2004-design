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
        "repo": "dsh-chatgpt-bridge",
        "name": "dsh-chatgpt-bridge",
        "category": "AGENT BRIDGE",
        "description_zh": "让 ChatGPT 创建、继续并控制 DeepSeek Harness Agent 会话的 MCP 桥接器。",
        "description_en": "An MCP bridge for creating, continuing, and controlling DeepSeek Harness agent sessions from ChatGPT.",
        "tech": ("JavaScript", "MCP", "ChatGPT"),
    },
    {
        "repo": "dsh-requirements-alignment",
        "name": "dsh-requirements-alignment",
        "category": "ALIGNMENT",
        "description_zh": "在执行前对齐关键需求，让 Agent 少猜测、少返工，同时保持工作流轻量。",
        "description_en": "Align important requirements before execution so agents guess less and rework less, without a heavyweight spec process.",
        "tech": ("TypeScript", "Agent", "Requirements"),
    },
    {
        "repo": "x-algorithm-auditor",
        "name": "X Algorithm Auditor",
        "category": "ANALYTICS",
        "description_zh": "基于公开 X 算法的本地、可解释 Analytics 审计工具。",
        "description_en": "Local, explainable X Analytics audits grounded in the public X algorithm.",
        "tech": ("Python", "Analytics", "Explainable"),
    },
    {
        "repo": "DraftPulse",
        "name": "DraftPulse",
        "category": "CREATOR TOOL",
        "description_zh": "面向 X/Twitter 的 AI 回复草稿与互动洞察浏览器扩展。",
        "description_en": "AI-assisted reply drafting and engagement insights for X/Twitter.",
        "tech": ("JavaScript", "Browser Extension", "AI"),
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
        "### `// 最近发布`"
        if language == "zh"
        else "### `// LATEST_RELEASES` - Recently shipped"
    )
    lines = [heading, "", "<table>"]
    for index in range(0, len(PROJECTS), 2):
        lines.append("  <tr>")
        for project in PROJECTS[index : index + 2]:
            lines.extend(project_cell(project, releases[project["repo"]], language))
        lines.append("  </tr>")
    lines.append("</table>")
    return "\n".join(lines)


def render_snapshot(profile: dict, repositories: list[dict], language: str) -> str:
    originals = [
        repo for repo in repositories if not repo.get("fork") and not repo.get("archived")
    ]
    public_repos = int(profile["public_repos"])
    original_count = len(originals)
    stars = sum(int(repo.get("stargazers_count", 0)) for repo in originals)
    followers = int(profile["followers"])
    snapshot_date = dt.datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()

    if language == "zh":
        heading = "### `// GitHub 快照`"
        labels = ("公开仓库", "活跃原创仓库", "原创仓库 Stars", "Followers")
        note = f"GitHub 公开数据快照 · {snapshot_date} · Stars 仅统计未归档原创仓库"
    else:
        heading = "### `// GITHUB_SNAPSHOT` - Public profile data"
        labels = (
            "Public repositories",
            "Active original repos",
            "Stars on original repos",
            "Followers",
        )
        note = (
            f"GitHub public-data snapshot · {snapshot_date} · "
            "Stars count non-archived original repositories only"
        )

    values = (public_repos, original_count, stars, followers)
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
    profile = api_get(f"/users/{urllib.parse.quote(OWNER)}")
    repositories = list_owner_repositories()
    releases = latest_releases()

    original = README_PATH.read_text(encoding="utf-8")
    updated = original
    updated = replace_block(updated, "latest-zh", render_latest(releases, "zh"))
    updated = replace_block(updated, "snapshot-zh", render_snapshot(profile, repositories, "zh"))
    updated = replace_block(updated, "latest-en", render_latest(releases, "en"))
    updated = replace_block(updated, "snapshot-en", render_snapshot(profile, repositories, "en"))

    if updated != original:
        README_PATH.write_text(updated, encoding="utf-8", newline="\n")
        print("README generated sections refreshed.")
    else:
        print("README generated sections already current.")


if __name__ == "__main__":
    main()
