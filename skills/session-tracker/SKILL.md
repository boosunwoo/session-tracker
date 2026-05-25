---
name: session-tracker
description: Save a human-readable summary of the current Claude Code session to ~/claude-sessions/ (title, 3-5 line summary, key decisions, modified files, and a resume command) and update INDEX.md so the user can later browse past sessions and continue them. Use when the user asks to "save this session", "summarize what we did", types /session-tracker, or is wrapping up a conversation worth remembering.
---

# Session Tracker

Save the current Claude Code session as a browseable markdown record in `~/claude-sessions/` and rebuild the index.

The user reviews these files later to remember what each session was about and to resume the right one with `claude --resume <id>`.

## Steps

1. **Extract raw session data** by running the bundled script with no `--write` flag — it prints JSON only:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/session-tracker/extract.py --current
   ```

   The JSON contains: `session_id`, `ai_title`, `cwd`, `start_time`, `end_time`, `user_prompts` (list), `file_edits` (list of `{tool, path}`), `tool_uses` (counts).

2. **Compose a 3–5 line summary.** Read the user prompts plus what you remember of your responses this session. Focus on:
   - What the user was trying to accomplish (the goal, not the literal first prompt)
   - The path taken (key approach choices)
   - What got completed vs. what is still open

   Keep it under 5 lines. Write it for future-self, not as a sales pitch — concrete nouns, no fluff.

3. **List key decisions** as 3–7 markdown bullets. Pull from explicit choices in the conversation: storage paths chosen, libraries picked, tradeoffs accepted, things explicitly ruled out. Skip mechanical actions ("ran tests"); keep judgment calls ("chose Python over Node because portability").

4. **Write the record.** Re-run the script with `--write` and pass the summary and decisions as flags. Use a heredoc or quoted strings; the script handles slug generation, file naming, removing any stale file for the same session_id, and rebuilding `INDEX.md`:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/session-tracker/extract.py --current --write \
     --summary "$(cat <<'EOF'
   <your 3-5 line summary here>
   EOF
   )" \
     --decisions "$(cat <<'EOF'
   - decision 1
   - decision 2
   - decision 3
   EOF
   )"
   ```

5. **Report** the saved path returned by the script (e.g. `~/claude-sessions/2026-05-25-15-04-foo.md`). One line is enough.

## Notes

- **Idempotent.** Running this skill again in the same session OVERWRITES the existing record (matched by `session_id`). The user can call you multiple times to refine the summary as work progresses.
- **Auto-save exists.** A `SessionEnd` hook calls `extract.py --from-hook --write --auto` automatically when the user exits Claude Code — that produces a placeholder summary. This skill is for *replacing* that placeholder with a real summary when the user asks.
- **Don't invent decisions.** If there are no clear judgment calls in the session, leave `--decisions` empty. The script will omit the section.
- **Don't include tool-result dumps in the summary.** The user already has the raw transcript; the value of this file is the *distillation*.
- **Override the title when the auto-generated one is wrong.** The `ai_title` in the JSON comes from Claude Code's early-conversation heuristic and often doesn't reflect what the session actually accomplished. If it's misleading, pass `--title "<better title>"` to the `--write` invocation — this also drives the filename slug. Pick a title in the same language as the conversation, 4–8 words, concrete nouns.
- **Storage location is fixed at `~/claude-sessions/`.** This is intentional: a stable, well-known path the user can browse with any file manager, sync via dotfiles, or back up independently of the plugin.
