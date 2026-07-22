#!/usr/bin/env node
// build-session-briefing.js — shared briefing text for sessionStart hooks
// Consumed by Cursor sessionStart and Claude gsd-session-state.sh (via node).

'use strict';

const fs = require('fs');
const path = require('path');

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

function headLines(text, n) {
  return String(text || '').split(/\r?\n/).slice(0, n).join('\n');
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
  if (fs.existsSync(planning)) walk(planning, 0);
  return found;
}

/**
 * Build additional_context briefing for session start.
 * @param {{ workspaceRoots?: string[], root?: string }} opts
 * @returns {{ present: boolean, text: string, root: string|null }}
 */
function buildSessionBriefing(opts) {
  const root = resolveRepoRoot(opts || {});
  if (!root) {
    return {
      present: false,
      root: null,
      text: 'gsd- no .planning/ workflow found — run /gsd-new-project to start a tracked workflow. See CONTINUITY.md after init.',
    };
  }

  const planning = path.join(root, '.planning');
  const statePath = path.join(planning, 'STATE.md');
  const snapPath = path.join(planning, 'SESSION_SNAP.md');
  const handoffPath = path.join(planning, 'HANDOFF.json');
  const graphPath = path.join(planning, 'graphs', 'GRAPH_REPORT.md');
  const continuityPath = path.join(planning, 'CONTINUITY.md');

  const parts = [
    'gsd- Claude↔Cursor continuity briefing (SSOT=.planning/; see CONTINUITY.md)',
    '',
  ];

  if (fs.existsSync(statePath)) {
    const state = fs.readFileSync(statePath, 'utf8');
    parts.push('## STATE.md (excerpt)', '', headLines(state, 22), '');
  } else {
    parts.push('## STATE.md', '', 'Missing — reconstruct via /gsd-resume-work', '');
  }

  if (fs.existsSync(snapPath)) {
    parts.push('## SESSION_SNAP.md', '', fs.readFileSync(snapPath, 'utf8').trim(), '');
  } else {
    parts.push('## SESSION_SNAP.md', '', 'Absent — no prior stop snap; rely on STATE + /gsd-resume-work', '');
  }

  const continueHere = findContinueHere(root);
  const handoffPresent = fs.existsSync(handoffPath);
  if (handoffPresent || continueHere.length) {
    parts.push(
      '## Resume artifacts',
      '',
      'Resume artifact present — run `/gsd-resume-work` before starting new work.',
      handoffPresent ? '- `.planning/HANDOFF.json`' : '',
      ...continueHere.map((p) => `- \`${p}\``),
      '',
    );
  } else {
    parts.push(
      '## Resume artifacts',
      '',
      'No HANDOFF / .continue-here — use STATE + SESSION_SNAP; `/gsd-next` if unsure.',
      '',
    );
  }

  if (fs.existsSync(graphPath)) {
    parts.push(
      '## Graphify (GRAPH_REPORT.md excerpt)',
      '',
      headLines(fs.readFileSync(graphPath, 'utf8'), 40),
      '',
      'Prefer `/gsd-graphify query <term>` before broad codebase search.',
      '',
    );
  } else {
    parts.push(
      '## Graphify',
      '',
      'Graph missing — run `/gsd-graphify build` to create `.planning/graphs/`.',
      '',
    );
  }

  if (fs.existsSync(continuityPath)) {
    parts.push('Playbook: `.planning/CONTINUITY.md`');
  }

  return { present: true, root, text: parts.filter((p, i, a) => !(p === '' && a[i - 1] === '')).join('\n') };
}

module.exports = {
  buildSessionBriefing,
  resolveRepoRoot,
  findPlanningRoot,
};

if (require.main === module) {
  const args = process.argv.slice(2);
  let root;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--root' && args[i + 1]) root = args[++i];
  }
  const result = buildSessionBriefing({ root, workspaceRoots: root ? [root] : [] });
  process.stdout.write(result.text);
}
