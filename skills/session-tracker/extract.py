#!/usr/bin/env python3
"""Extract a Claude Code session from its JSONL transcript and save a
human-readable markdown record into ~/claude-sessions/, then rebuild INDEX.md.

Usage:
  python3 extract.py --current                       # print JSON only
  python3 extract.py --current --write --auto        # auto save (no AI summary)
  python3 extract.py --session-id <id> --write \\
      --summary "..." --decisions "- ..."             # rich save
  python3 extract.py --from-hook --write --auto      # called by SessionEnd hook (reads stdin)
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SESSIONS_DIR = Path.home() / "claude-sessions"
PROJECTS_DIR = Path.home() / ".claude" / "projects"


def find_latest_jsonl():
    files = list(PROJECTS_DIR.rglob("*.jsonl"))
    if not files:
        sys.exit("No session transcripts found in ~/.claude/projects/")
    return max(files, key=lambda p: p.stat().st_mtime)


def find_jsonl_by_session_id(session_id):
    for f in PROJECTS_DIR.rglob("*.jsonl"):
        try:
            with f.open() as fh:
                first = fh.readline()
                if session_id in first:
                    return f
        except OSError:
            continue
    sys.exit(f"No transcript found for session {session_id}")


def parse_jsonl(path):
    data = {
        "session_id": None,
        "ai_title": None,
        "cwd": None,
        "start_time": None,
        "end_time": None,
        "user_prompts": [],
        "file_edits": [],
        "tool_uses": {},
    }
    with path.open() as fh:
        for line in fh:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = e.get("type")
            ts = e.get("timestamp")
            if ts:
                if not data["start_time"]:
                    data["start_time"] = ts
                data["end_time"] = ts
            if not data["session_id"]:
                data["session_id"] = e.get("sessionId")
            if not data["cwd"]:
                data["cwd"] = e.get("cwd")
            if t == "ai-title":
                data["ai_title"] = e.get("aiTitle") or data["ai_title"]
            elif t == "user":
                msg = e.get("message", {})
                c = msg.get("content") if isinstance(msg, dict) else None
                if isinstance(c, str):
                    stripped = c.lstrip()
                    if stripped and not stripped.startswith("<"):
                        data["user_prompts"].append(c)
            elif t == "assistant":
                msg = e.get("message", {})
                c = msg.get("content", []) if isinstance(msg, dict) else []
                if isinstance(c, list):
                    for block in c:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            name = block.get("name", "?")
                            data["tool_uses"][name] = data["tool_uses"].get(name, 0) + 1
                            if name in ("Edit", "Write", "NotebookEdit"):
                                fp = (block.get("input") or {}).get("file_path")
                                if fp:
                                    data["file_edits"].append({"tool": name, "path": fp})
    if not data["ai_title"]:
        first = data["user_prompts"][0] if data["user_prompts"] else "(untitled)"
        data["ai_title"] = " ".join(first.split())[:60]
    return data


PLACEHOLDER_SUMMARY = "_(No summary yet — auto-saved placeholder. Run `/session-tracker` to add a real summary.)_"


def slugify(text, maxlen=40):
    text = text.lower().strip()
    # Keep ASCII letters/digits and CJK characters; replace others with hyphen
    text = re.sub(r"[^a-z0-9぀-鿿]+", "-", text)
    text = text.strip("-")
    return text[:maxlen] or "session"


def fmt_iso(iso):
    if not iso:
        return "?"
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return iso


def build_markdown(data, summary="", decisions=""):
    sid = data["session_id"]
    title = data["ai_title"]
    lines = [
        "---",
        f"session_id: {sid}",
        f"title: {title}",
        f"start: {fmt_iso(data['start_time'])}",
        f"end: {fmt_iso(data['end_time'])}",
        f"cwd: {data['cwd'] or '(unknown)'}",
        "---",
        "",
        f"# {title}",
        "",
        "## Summary",
        "",
        (summary or PLACEHOLDER_SUMMARY).strip(),
        "",
    ]
    if decisions.strip():
        lines += ["## Key Decisions", "", decisions.strip(), ""]

    lines += ["## User Prompts", ""]
    for i, p in enumerate(data["user_prompts"], 1):
        excerpt = " ".join(p.split())
        if len(excerpt) > 240:
            excerpt = excerpt[:240] + "…"
        lines.append(f"{i}. {excerpt}")
    if not data["user_prompts"]:
        lines.append("_(none)_")
    lines.append("")

    if data["file_edits"]:
        lines += ["## Modified Files", ""]
        seen = set()
        for ed in data["file_edits"]:
            if ed["path"] not in seen:
                lines.append(f"- `{ed['path']}` ({ed['tool']})")
                seen.add(ed["path"])
        lines.append("")

    if data["tool_uses"]:
        lines += ["## Tool Usage", ""]
        for name, count in sorted(data["tool_uses"].items(), key=lambda x: -x[1]):
            lines.append(f"- {name}: {count}")
        lines.append("")

    lines += [
        "## Resume This Session",
        "",
        "```bash",
        f"claude --resume {sid}",
        "```",
        "",
    ]
    return "\n".join(lines)


def parse_frontmatter(text):
    """Extract YAML-ish frontmatter (k: v lines) and a summary first-line."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    fm = {}
    for line in text[4:end].split("\n"):
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    body = text[end + 5 :]
    if "## Summary" in body:
        section = body.split("## Summary", 1)[1].split("\n## ", 1)[0].strip()
        fm["summary"] = section.split("\n")[0][:200]
    return fm


def rebuild_index():
    sessions = []
    for f in SESSIONS_DIR.glob("*.md"):
        if f.name == "INDEX.md":
            continue
        try:
            meta = parse_frontmatter(f.read_text(encoding="utf-8"))
        except OSError:
            continue
        if meta:
            meta["file"] = f
            sessions.append(meta)
    sessions.sort(key=lambda s: s.get("start", ""), reverse=True)

    by_date = {}
    for s in sessions:
        date = (s.get("start", "") or "")[:10] or "unknown"
        by_date.setdefault(date, []).append(s)

    lines = [
        "# Claude Code Sessions",
        "",
        f"_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
        f"**{len(sessions)} sessions** recorded. New sessions are added automatically when Claude Code exits. Click any entry below to see details and the command to resume it.",
        "",
        "---",
        "",
    ]
    for date in sorted(by_date.keys(), reverse=True):
        lines.append(f"## {date}")
        lines.append("")
        for s in by_date[date]:
            time = (s.get("start", "") or "")[11:16] or "?"
            title = s.get("title", "(untitled)")
            rel = s["file"].name
            hook = (s.get("summary", "") or "").strip()
            if hook.startswith("_(No summary"):
                hook = ""
            if hook:
                lines.append(f"- `{time}` — [{title}](./{rel}) — {hook}")
            else:
                lines.append(f"- `{time}` — [{title}](./{rel}) _(auto-saved)_")
        lines.append("")

    if not sessions:
        lines.append("_(No sessions saved yet.)_")

    (SESSIONS_DIR / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")


def remove_existing_for_session(sid, keep=None):
    for existing in SESSIONS_DIR.glob("*.md"):
        if existing.name == "INDEX.md" or existing == keep:
            continue
        try:
            head = existing.read_text(encoding="utf-8")[:500]
            if f"session_id: {sid}" in head:
                existing.unlink()
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--current", action="store_true", help="Use most-recently-modified transcript")
    ap.add_argument("--session-id", help="Specific session ID to load")
    ap.add_argument("--from-hook", action="store_true",
                    help="Read JSON from stdin (Claude Code hook payload) for session_id")
    ap.add_argument("--write", action="store_true", help="Write markdown file and rebuild index")
    ap.add_argument("--auto", action="store_true", help="Auto mode (no AI summary required)")
    ap.add_argument("--summary", default="", help="AI-generated summary text")
    ap.add_argument("--decisions", default="", help="AI-generated decisions list (markdown)")
    ap.add_argument("--title", default="", help="Override the AI-generated session title (also affects filename slug)")
    args = ap.parse_args()

    if args.from_hook:
        try:
            payload = json.load(sys.stdin)
        except json.JSONDecodeError:
            payload = {}
        sid = payload.get("session_id")
        if sid:
            path = find_jsonl_by_session_id(sid)
        else:
            path = find_latest_jsonl()
    elif args.session_id:
        path = find_jsonl_by_session_id(args.session_id)
    else:
        path = find_latest_jsonl()

    data = parse_jsonl(path)

    if args.title:
        data["ai_title"] = args.title

    if not args.write:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        dt = datetime.fromisoformat((data["start_time"] or "").replace("Z", "+00:00"))
        prefix = dt.strftime("%Y-%m-%d-%H-%M")
    except (ValueError, AttributeError):
        prefix = "unknown"

    slug = slugify(data["ai_title"])
    file_path = SESSIONS_DIR / f"{prefix}-{slug}.md"

    remove_existing_for_session(data["session_id"], keep=file_path)

    md = build_markdown(data, summary=args.summary, decisions=args.decisions)
    file_path.write_text(md, encoding="utf-8")

    rebuild_index()
    print(f"Saved: {file_path}")


if __name__ == "__main__":
    main()
