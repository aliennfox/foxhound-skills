---
name: openclaw-backup-rotation
description: Maintain a lean OpenClaw backup workflow for config snapshots and bundle archives. Use when the user asks to back up OpenClaw, rotate old backups, keep only the latest and second-latest snapshot, clean stale backup files, or refresh a new bundled backup tarball under ~/.openclaw.
---

# OpenClaw Backup Rotation

Use this skill when working on OpenClaw backup hygiene under `~/.openclaw`.

## Goal

Keep backup state simple and predictable:

- Keep live files untouched
- Keep only two generations of single-file backups: `latest` and `second-latest`
- Delete anything older when creating a new backup
- Keep one fresh bundled archive in `~/.openclaw/workspace/data/`
- Prefer timestamped names: `YYYYMMDD-HHMMSS`

## Scope

Default files covered by this workflow:

- `~/.openclaw/openclaw.json`
- `~/.openclaw/cron/jobs.json`
- `~/.openclaw/agents/main/agent/auth-profiles.json`

Default bundle output:

- `~/.openclaw/workspace/data/openclaw-backup-<timestamp>.tar.gz`

## Workflow

1. Inspect existing backups for the three files above and the bundle archive.
2. Normalize backup names to this format when needed:
   - `<filename>.backup-YYYYMMDD-HHMMSS`
   - optional suffix only when it adds real value
3. Before creating a new backup:
   - identify the current `latest`
   - identify the current `second-latest`
   - delete anything older than those two generations
4. Create a fresh timestamped backup for each live file.
5. After creating the new backups:
   - keep the new backups as `latest`
   - keep the previous `latest` as `second-latest`
   - delete the old `second-latest`
6. Refresh the bundled archive:
   - delete older `openclaw-backup-*.tar.gz` archives
   - create one new bundle archive with the same timestamp
7. Report exactly what was removed and what was created.

## Safety Rules

- Never modify the live source files while doing backup rotation.
- Never delete the live files.
- If a file is missing, report it and continue with the remaining files.
- If backup naming is messy, normalize only the files clearly belonging to this workflow.
- Do not sweep unrelated `backup` or `old` files from browser caches, node_modules, or project worktrees.

## Decision Rules

- Treat `auth-profiles.json` as in-scope for backup rotation when the user asks for the full OpenClaw backup workflow.
- If there is only one existing backup, keep it as `second-latest` after creating the new one.
- If there are no existing backups, create the new set and the new bundle only.
- If the user explicitly asks to keep more than two generations, follow the user instead of this default.

## Preferred Output

Answer with a concise checklist:

- removed old backups
- kept current live files
- created new single-file backups
- created new bundle archive
- list resulting paths
