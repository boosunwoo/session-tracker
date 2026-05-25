# session-tracker

A Claude Code plugin that saves each session as a browseable markdown record so you can later remember what you discussed and continue the right one.

## What problem this solves

Claude Code already saves the raw JSONL transcript of every session in `~/.claude/projects/`, and `claude --resume <id>` can revive any of them. But:

- The JSONL files are not human-readable.
- The session picker only shows AI-generated titles, which are easy to forget.
- After a few weeks you have dozens of sessions and no easy way to find the one you want.

`session-tracker` writes a clean markdown file per session into `~/claude-sessions/`, keeps a date-grouped `INDEX.md`, and gives you a one-line `claude --resume <id>` command to continue any past session.

## Features

- **Auto-save on exit.** A `SessionEnd` hook records every session automatically — no action needed.
- **Manual refinement.** Type `/session-tracker` (or ask Claude to "save this session") to replace the auto-saved placeholder with a real AI-generated 3–5 line summary and a list of key decisions.
- **Idempotent.** Multiple saves of the same session overwrite the same file (matched by `session_id`).
- **Index rebuilt from scratch every time.** No drift, no corruption — the `INDEX.md` is regenerated from the frontmatter of every session file.
- **Zero external dependencies.** Python 3 standard library only.

## Installation

From a Claude Code session:

```
/plugin marketplace add github.com/boosunwoo/session-tracker
/plugin install session-tracker
```

Or, if you've added this plugin to an existing marketplace, just:

```
/plugin install session-tracker@<marketplace-name>
```

That's it — the `SessionEnd` hook registers automatically and you'll see your first record in `~/claude-sessions/` the next time you exit Claude Code.

## Usage

### Automatic (default)

Just use Claude Code normally. When you exit (`/exit`, `Ctrl+D`, or closing the terminal), the hook writes a placeholder summary along with all the metadata (prompts, file edits, tool usage, resume command).

### Manual (richer summary)

When you're wrapping up a session worth remembering, ask Claude to save it:

```
/session-tracker
```

or in natural language:

> save this session
> summarize what we did today
> 이번 세션 정리해줘

Claude will read the conversation, write a 3–5 line summary and a list of key decisions, then overwrite the auto-saved record. The file path and filename do not change.

### Browse past sessions

```bash
cat ~/claude-sessions/INDEX.md
```

Or open `~/claude-sessions/` in any editor or file manager. Each entry includes a `claude --resume <id>` command you can copy-paste to continue that conversation.

## File layout

```
~/claude-sessions/
├── INDEX.md                                    # date-grouped overview
├── 2026-05-25-14-30-bug-fix-in-auth.md         # one file per session
├── 2026-05-25-15-04-session-tracker-setup.md
└── ...
```

Each session file contains:

```
---
session_id: <uuid>
title: <AI-generated title>
start: 2026-05-25 14:30:00
end: 2026-05-25 14:52:00
cwd: /path/to/working/dir
---

# <title>

## Summary
<3-5 line distillation>

## Key Decisions
- <judgment calls made during the session>

## User Prompts
1. <first user prompt>
2. ...

## Modified Files
- /path/to/file (Edit)

## Tool Usage
- Bash: 12
- Read: 4

## Resume This Session
```bash
claude --resume <uuid>
```
```

## Configuration

None. The plugin reads from `~/.claude/projects/` and writes to `~/claude-sessions/` with sensible defaults.

If you want to disable the auto-save hook but keep `/session-tracker` for manual use, disable the plugin's hook in `/plugin settings`.

## Limitations

- **Per-machine only.** Session JSONLs live locally on each machine; sessions from one computer can't be resumed on another. (The markdown summaries can be synced via git or any file-sync tool — `~/claude-sessions/` is just a folder.)
- **Linux/macOS tested.** Should work on Windows too (the script uses `pathlib.Path.home()`), but not formally verified.
- **Python 3 required.** The bundled `extract.py` uses standard library only, no external pip packages.

## Why store in `~/claude-sessions/` and not under `~/.claude/`?

So the user can find it. A hidden folder under `~/.claude/` would be hard to discover; a top-level folder is browseable by anyone who opens a file manager.

## License

MIT — see [LICENSE](./LICENSE).
