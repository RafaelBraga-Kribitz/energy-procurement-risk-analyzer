#!/usr/bin/env node
// write-session-snap.js — overwrite .planning/SESSION_SNAP.md for Claude↔Cursor handoff
//
// Usage:
//   node write-session-snap.js [--runtime cursor|claude-code] [--root <repoRoot>]
//
// Fail-open: never throws to caller; returns { ok, path?, error? }.
// Safe to require() from stop hooks or invoke as CLI.

'use strict';

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

/**
 * Walk upward from startDir looking for a directory that contains `.planning/`.
 * @param {string} startDir
 * @returns {string|null}
 */
function findPlanningRoot(startDir) {
  let dir = path.resolve(startDir || process.cwd());
  for (let i = 0; i < 24; i++) {
    if (fs.existsSync(path.join(dir, '.planning'))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

/**
 * Resolve repo root from optional explicit root, workspace_roots, or cwd.
 * @param {{ root?: string, workspaceRoots?: string[] }} opts
 * @returns {string|null}
 */
function resolveRepoRoot(opts) {
  const optsSafe = opts || {};
  if (optsSafe.root && fs.existsSync(path.join(optsSafe.root, '.planning'))) {
    return path.resolve(optsSafe.root);
  }
  const roots = optsSafe.workspaceRoots || [];
  for (const wr of roots) {
    if (!wr || typeof wr !== 'string') continue;
    const found = findPlanningRoot(wr);
    if (found) return found;
  }
  return findPlanningRoot(process.cwd());
}

function parseFrontmatter(text) {
  const m = String(text || '').match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!m) return {};
  const out = {};
  for (const line of m[1].split(/\r?\n/)) {
    const idx = line.indexOf(':');
    if (idx < 1) continue;
    const key = line.slice(0, idx).trim();
    let val = line.slice(idx + 1).trim();
    if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
      val = val.slice(1, -1);
    }
    out[key] = val;
  }
  return out;
}

function extractSessionContinuity(text) {
  const m = String(text || '').match(/## Session Continuity\s*\r?\n([\s\S]*?)(?=\r?\n## |\r?\n# |\s*$)/);
  return m ? m[1].trim() : '';
}

function gitMeta(repoRoot) {
  const meta = { head: null, dirty_count: 0 };
  try {
    meta.head = execSync('git rev-parse --short HEAD', {
      cwd: repoRoot,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
      timeout: 5000,
    }).trim();
  } catch { /* ignore */ }
  try {
    const status = execSync('git status --porcelain', {
      cwd: repoRoot,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
      timeout: 8000,
    });
    meta.dirty_count = status.split(/\r?\n/).filter((l) => l.trim().length > 0).length;
  } catch { /* ignore */ }
  return meta;
}

function findContinueHere(repoRoot) {
  const planning = path.join(repoRoot, '.planning');
  const found = [];
  const walk = (dir, depth) => {
    if (depth > 3 || found.length >= 8) return;
    let entries;
    try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const ent of entries) {
      const full = path.join(dir, ent.name);
      if (ent.isFile() && /^\.continue-here.*\.md$/i.test(ent.name)) {
        found.push(path.relative(repoRoot, full).replace(/\\/g, '/'));
      } else if (ent.isDirectory() && !ent.name.startsWith('.') && ent.name !== 'node_modules') {
        walk(full, depth + 1);
      }
    }
  };
  walk(planning, 0);
  return found;
}

/**
 * Write SESSION_SNAP.md for the given runtime.
 * @param {{ runtime?: string, root?: string, workspaceRoots?: string[] }} opts
 * @returns {{ ok: boolean, path?: string, error?: string, skipped?: boolean }}
 */
function writeSessionSnap(opts) {
  try {
    const runtime = (opts && opts.runtime) || 'unknown';
    const repoRoot = resolveRepoRoot(opts || {});
    if (!repoRoot) {
      return { ok: true, skipped: true, error: 'no .planning/ found' };
    }

    const planningDir = path.join(repoRoot, '.planning');
    const statePath = path.join(planningDir, 'STATE.md');
    const snapPath = path.join(planningDir, 'SESSION_SNAP.md');
    const handoffPath = path.join(planningDir, 'HANDOFF.json');
    const graphReport = path.join(planningDir, 'graphs', 'GRAPH_REPORT.md');

    let stateText = '';
    let fm = {};
    let continuity = '';
    if (fs.existsSync(statePath)) {
      stateText = fs.readFileSync(statePath, 'utf8');
      fm = parseFrontmatter(stateText);
      continuity = extractSessionContinuity(stateText);
    }

    const git = gitMeta(repoRoot);
    const continueHere = findContinueHere(repoRoot);
    const handoffPresent = fs.existsSync(handoffPath);
    const graphPresent = fs.existsSync(graphReport);
    const timestamp = new Date().toISOString();
    const stoppedAt = fm.stopped_at || '';
    const nextHint = stoppedAt
      ? stoppedAt
      : 'run /gsd-resume-work or /gsd-next';

    const lines = [
      '---',
      `runtime: ${runtime}`,
      `timestamp: "${timestamp}"`,
      `head: ${git.head || 'unknown'}`,
      `dirty_count: ${git.dirty_count}`,
      `phase: ${fm.current_phase || fm.phase || ''}`,
      `phase_name: ${fm.current_phase_name || ''}`,
      `status: ${fm.status || ''}`,
      `stopped_at: ${JSON.stringify(stoppedAt)}`,
      `handoff_json: ${handoffPresent}`,
      `continue_here_count: ${continueHere.length}`,
      `graph_report: ${graphPresent}`,
      '---',
      '',
      '# Session Snap',
      '',
      `Auto-written on **${runtime}** agent stop for Claude Code ↔ Cursor continuity.`,
      'See `.planning/CONTINUITY.md`.',
      '',
      '## Position',
      '',
      `- Phase: ${fm.current_phase || '?'} (${fm.current_phase_name || '?'})`,
      `- Status: ${fm.status || '?'}`,
      `- Stopped at: ${stoppedAt || '(none in STATE)'}`,
      `- Git HEAD: ${git.head || 'unknown'} (${git.dirty_count} dirty path(s))`,
      '',
      '## Resume artifacts',
      '',
      `- HANDOFF.json: ${handoffPresent ? '.planning/HANDOFF.json' : 'absent'}`,
      continueHere.length
        ? `- .continue-here: ${continueHere.map((p) => `\`${p}\``).join(', ')}`
        : '- .continue-here: absent',
      graphPresent
        ? '- Graph: `.planning/graphs/GRAPH_REPORT.md`'
        : '- Graph: missing — run `/gsd-graphify build`',
      '',
      '## Next hint',
      '',
      nextHint,
      '',
    ];

    if (continuity) {
      lines.push('## STATE Session Continuity', '', continuity, '');
    }

    lines.push(
      '## Resume',
      '',
      '1. Read this file + `.planning/STATE.md`',
      '2. If HANDOFF / `.continue-here` present → `/gsd-resume-work`',
      '3. Else → `/gsd-next` or continue from Next hint',
      '',
    );

    fs.writeFileSync(snapPath, lines.join('\n'), 'utf8');
    return { ok: true, path: snapPath };
  } catch (err) {
    return { ok: false, error: String(err && err.message ? err.message : err) };
  }
}

module.exports = {
  writeSessionSnap,
  resolveRepoRoot,
  findPlanningRoot,
  parseFrontmatter,
};

if (require.main === module) {
  const args = process.argv.slice(2);
  let runtime = 'unknown';
  let root;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--runtime' && args[i + 1]) {
      runtime = args[++i];
    } else if (args[i] === '--root' && args[i + 1]) {
      root = args[++i];
    }
  }
  const result = writeSessionSnap({ runtime, root });
  if (!result.ok) {
    process.stderr.write(`write-session-snap failed: ${result.error}\n`);
    process.exit(0); // fail-open
  }
  if (result.path) {
    process.stdout.write(`wrote ${result.path}\n`);
  }
  process.exit(0);
}
