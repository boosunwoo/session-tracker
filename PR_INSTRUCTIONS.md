# How to publish `session-tracker` to the official marketplace

Two stages: (1) publish your plugin to a public GitHub repo, (2) open a PR against the official marketplace adding your entry.

---

## Stage 1 — Push the plugin to GitHub

The contents of this `session-tracker-plugin/` folder are the plugin. The recommended layout is to make a dedicated GitHub repo where the entire repo *is* the plugin.

```bash
cd ~/Desktop/session-tracker-plugin
git init
git add .
git commit -m "Initial commit: session-tracker plugin"
git branch -M main
git remote add origin https://github.com/boosunwoo/session-tracker.git
git push -u origin main
```

After pushing, **grab the commit SHA** — you'll need it for the marketplace entry:

```bash
git rev-parse HEAD
# e.g. 3f9a1b2c4d5e6f7890abcdef1234567890abcdef
```

Then tag a release (recommended so the marketplace pins a specific version):

```bash
git tag v0.1.0
git push --tags
```

---

## Stage 2 — Submit a PR to the official marketplace

The official marketplace repo is hosted by Anthropic. The exact URL is visible in your installed marketplace at:

```bash
cat ~/.claude/plugins/marketplaces/claude-plugins-official/.claude-plugin/marketplace.json | head -10
```

Steps:

1. **Fork** the `anthropics/claude-plugins` (or equivalent) repo on GitHub.
2. **Clone** your fork locally.
3. **Open** `.claude-plugin/marketplace.json`.
4. **Add** the following entry to the `plugins` array (insert alphabetically by `name`):

```json
{
  "name": "session-tracker",
  "description": "Save each Claude Code session as a browseable markdown record in ~/claude-sessions/ with title, summary, key decisions, modified files, and a resume command. Auto-saves on session end and supports manual refinement via /session-tracker.",
  "author": {
    "name": "boosunwoo"
  },
  "category": "productivity",
  "source": {
    "source": "git",
    "url": "https://github.com/boosunwoo/session-tracker.git",
    "ref": "v0.1.0",
    "sha": "PASTE_COMMIT_SHA_HERE"
  },
  "homepage": "https://github.com/boosunwoo/session-tracker"
}
```

> **Note:** Replace `PASTE_COMMIT_SHA_HERE` with the actual SHA from `git rev-parse v0.1.0`.

5. **Commit** with a clear message:

   ```
   Add session-tracker plugin
   
   session-tracker auto-saves Claude Code sessions as markdown records
   in ~/claude-sessions/ for later browsing and resumption.
   ```

6. **Push** and **open a PR** against the upstream repo's main branch.

7. **Wait for review.** Anthropic's maintainers may request changes (naming, description, license, README polish).

---

## Pre-flight checklist before submitting the PR

- [ ] Plugin loads without errors locally: `/plugin install ./~/Desktop/session-tracker-plugin`
- [ ] `SessionEnd` hook fires (test with `/exit` then check `~/claude-sessions/`)
- [ ] `/session-tracker` rewrites the placeholder with a real summary
- [ ] `README.md` renders well on GitHub (preview it)
- [ ] `LICENSE` file is present
- [ ] `plugin.json` has correct `name`, `version`, `description`, `repository`
- [ ] No hardcoded user paths in `extract.py` (uses `Path.home()` ✓)
- [ ] All hook commands use `${CLAUDE_PLUGIN_ROOT}` ✓

---

## Alternative: skip the official PR and self-host

If you don't want to wait for review, anyone can install your plugin directly from your GitHub repo:

```
/plugin marketplace add github.com/boosunwoo/session-tracker
/plugin install session-tracker
```

Just make a one-line marketplace manifest at the root of your repo as `.claude-plugin/marketplace.json`:

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "boosunwoo-plugins",
  "description": "boosunwoo's personal Claude Code plugins",
  "owner": {
    "name": "boosunwoo"
  },
  "plugins": [
    {
      "name": "session-tracker",
      "description": "Save each Claude Code session as a browseable markdown record.",
      "author": { "name": "boosunwoo" },
      "category": "productivity",
      "source": "."
    }
  ]
}
```

But this duplicates the plugin metadata. The cleaner choice is to host the plugin alone and rely on the official marketplace (or a friend's marketplace) to list it.
