# Claude Code ↔ Cursor Continuity

Cross-runtime handoff for this project. Chat history does **not** travel between Claude Code and Cursor — only files under `.planning/` do.

## Source of truth

| Artifact | Role |
|----------|------|
| `.planning/STATE.md` | Phase, status, decisions, blockers, `stopped_at` |
| `.planning/SESSION_SNAP.md` | Lightweight last-session snapshot (auto-written on agent stop) |
| `.planning/HANDOFF.json` + `.continue-here.md` | Full mid-task pause (from `/gsd-pause-work`) |
| `.planning/phases/**/PLAN.md` + `SUMMARY.md` | Plan completion = SUMMARY present |
| `.planning/graphs/` | Canonical graphify outputs (`GRAPH_REPORT.md`, `graph.json`) |

GSD skills/hooks live in per-runtime installs (`~/.claude`, `~/.cursor`, project `.claude`/`.cursor`) and are **not** shared automatically. Re-sync after `/gsd-update` (see below).

## Switch / resume protocol

| Situation | Action |
|-----------|--------|
| Intentional switch | `/gsd-pause-work` → switch runtime → `/gsd-resume-work` |
| Usage limit / crash | Open other runtime → session briefing loads `SESSION_SNAP` + STATE → `/gsd-resume-work` or `/gsd-next` |
| Codebase orientation | Prefer `/gsd-graphify query <term>` or read `.planning/graphs/GRAPH_REPORT.md` before wide search |
| After GSD upgrade | Re-run skill sync (see below) |

**Do not** assume the other runtime’s chat, TodoWrite list, or transcripts are visible.

## Graphify

- Config: `graphify.enabled` / `graphify.auto_update` in `.planning/config.json`
- Canonical output: `.planning/graphs/` (staging dir `graphify-out/` is not the SSOT)
- CLI package: `graphifyy` (PyPI); command name: `graphify`
- Install: `uv tool install graphifyy` then ensure `~/.local/bin` is on `PATH`
  (Windows PowerShell: `$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"`)
- Manual rebuild: `/gsd-graphify build`
- Auto-update: after HEAD-advancing commits on the default branch, Cursor postToolUse
  and Claude PostToolUse both trigger `.planning/hooks/maybe-graphify-update.js`
  (Windows-friendly; Claude's bash hook also looks for `graphify` on PATH)

## Skill sync (after `/gsd-update`)

Keep pause/resume/next workflows aligned across runtimes. **Canonical source: Claude Code
`~/.claude/gsd-core/workflows/`** (Cursor skill wrappers are adapter-transformed — do not
blindly overwrite Cursor `skills/gsd-*` from Claude).

After updating GSD on one runtime, sync these workflow files to the other:

- `pause-work.md`
- `resume-project.md`
- `next.md`
- `sync-skills.md` (optional)

Targets: `~/.cursor/gsd-core/workflows/` and (if present) project `.cursor/gsd-core/workflows/`.

Or in either assistant follow `/gsd-sync-skills` for skill directories when the installer
supports your pair — dry-run first; prefer installer re-apply for Cursor-adapted skills.

This repo’s continuity kit also lives under `.planning/hooks/` (committed) so both
runtimes share SESSION_SNAP / briefing / graphify helpers regardless of skill skew.

## Hook behavior (local)

- **sessionStart**: injects STATE excerpt, `SESSION_SNAP`, handoff pointers, graph tip
- **stop**: overwrites `.planning/SESSION_SNAP.md` (fail-open)
- Claude: enable `hooks.community: true` in config so STATE head is injected at SessionStart
