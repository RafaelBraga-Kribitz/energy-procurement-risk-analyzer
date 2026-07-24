#!/usr/bin/env node
// maybe-graphify-update.js — Cursor/Claude parity for graphify auto-update after HEAD advances
// Mirrors gates from ~/.claude/hooks/gsd-graphify-update.sh (fail-open, non-blocking).
//
// Usage (from post-tool hook):
//   require('./maybe-graphify-update').maybeGraphifyUpdate({ toolName, command, repoRoot })

'use strict';

const fs = require('fs');
const path = require('path');
const { spawn, execSync } = require('child_process');

function findGraphifyBin() {
  const local = path.join(process.env.USERPROFILE || process.env.HOME || '', '.local', 'bin',
    process.platform === 'win32' ? 'graphify.exe' : 'graphify');
  if (fs.existsSync(local)) return local;
  try {
    const which = process.platform === 'win32' ? 'where.exe graphify' : 'command -v graphify';
    const out = execSync(which, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 3000 }).trim();
    const first = out.split(/\r?\n/).filter(Boolean)[0];
    if (first && fs.existsSync(first)) return first;
  } catch { /* ignore */ }
  return null;
}

function isHeadAdvancing(command) {
  const c = String(command || '');
  if (!c) return false;
  if (/git\s+commit\b/i.test(c)) return true;
  if (/git\s+merge\b/i.test(c)) return true;
  if (/git\s+pull\b/i.test(c)) return true;
  if (/git\s+rebase\s+--continue\b/i.test(c)) return true;
  if (/git\s+cherry-pick\b/i.test(c)) return true;
  if (/gsd-tools(\.cjs)?\s+query\s+commit\b/i.test(c)) return true;
  return false;
}

function readConfig(repoRoot) {
  try {
    return JSON.parse(fs.readFileSync(path.join(repoRoot, '.planning', 'config.json'), 'utf8'));
  } catch {
    return null;
  }
}

function defaultBranch(repoRoot, cfg) {
  if (cfg && cfg.git && cfg.git.base_branch) return cfg.git.base_branch;
  for (const cand of ['main', 'master', 'trunk']) {
    try {
      execSync(`git rev-parse --verify ${cand}`, {
        cwd: repoRoot,
        stdio: ['ignore', 'pipe', 'ignore'],
        timeout: 3000,
      });
      return cand;
    } catch { /* next */ }
  }
  return null;
}

function currentBranch(repoRoot) {
  try {
    return execSync('git rev-parse --abbrev-ref HEAD', {
      cwd: repoRoot,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
      timeout: 3000,
    }).trim();
  } catch {
    return null;
  }
}

/**
 * Fire-and-forget graphify update when gates pass.
 * @returns {{ triggered: boolean, reason?: string }}
 */
function maybeGraphifyUpdate(opts) {
  try {
    const optsSafe = opts || {};
    if (process.env.CI) return { triggered: false, reason: 'ci' };

    const toolName = String(optsSafe.toolName || '').toLowerCase();
    const command = optsSafe.command || '';
    // Cursor uses "Shell"; Claude uses "Bash"
    const isShell = /^(shell|bash|powershell|cmd)$/i.test(toolName) || toolName.includes('shell');
    if (!isShell) return { triggered: false, reason: 'not-shell' };
    if (!isHeadAdvancing(command)) return { triggered: false, reason: 'not-head-advancing' };

    const repoRoot = optsSafe.repoRoot;
    if (!repoRoot || !fs.existsSync(path.join(repoRoot, '.planning'))) {
      return { triggered: false, reason: 'no-planning' };
    }

    const cfg = readConfig(repoRoot);
    if (!cfg || cfg.graphify?.enabled !== true || cfg.graphify?.auto_update !== true) {
      return { triggered: false, reason: 'graphify-disabled' };
    }

    const def = defaultBranch(repoRoot, cfg);
    const cur = currentBranch(repoRoot);
    if (!def || !cur || def !== cur) {
      return { triggered: false, reason: 'not-default-branch' };
    }

    const graphifyBin = findGraphifyBin();
    if (!graphifyBin) return { triggered: false, reason: 'graphify-not-on-path' };

    const graphsDir = path.join(repoRoot, '.planning', 'graphs');
    fs.mkdirSync(graphsDir, { recursive: true });
    const lockFile = path.join(graphsDir, '.rebuild.lock');
    const statusFile = path.join(graphsDir, '.last-build-status.json');

    if (fs.existsSync(lockFile)) {
      try {
        const pid = parseInt(fs.readFileSync(lockFile, 'utf8').trim(), 10);
        if (pid && !Number.isNaN(pid)) {
          try {
            process.kill(pid, 0);
            return { triggered: false, reason: 'rebuild-in-flight' };
          } catch {
            // stale lock
          }
        }
      } catch { /* ignore */ }
    }

    let headSha = '';
    try {
      headSha = execSync('git rev-parse HEAD', {
        cwd: repoRoot,
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore'],
        timeout: 3000,
      }).trim();
    } catch { /* ignore */ }

    const msStart = Date.now();
    fs.writeFileSync(statusFile, JSON.stringify({
      ts: new Date().toISOString(),
      status: 'running',
      exit_code: null,
      duration_ms: null,
      head_at_build: headSha,
      graphify_version: null,
    }, null, 2) + '\n');

    // Detached rebuild via node child (Windows-friendly; no bash required)
    const runner = path.join(repoRoot, '.planning', 'hooks', 'run-graphify-rebuild.js');
    if (!fs.existsSync(runner)) {
      return { triggered: false, reason: 'runner-missing' };
    }

    const child = spawn(process.execPath, [runner, statusFile, lockFile, headSha, String(msStart), graphifyBin, repoRoot], {
      cwd: repoRoot,
      detached: true,
      stdio: 'ignore',
      windowsHide: true,
      env: { ...process.env, PATH: `${path.dirname(graphifyBin)}${path.delimiter}${process.env.PATH || ''}` },
    });
    try {
      fs.writeFileSync(lockFile, String(child.pid) + '\n');
    } catch { /* ignore */ }
    child.unref();

    return { triggered: true };
  } catch (err) {
    return { triggered: false, reason: String(err && err.message ? err.message : err) };
  }
}

module.exports = { maybeGraphifyUpdate, findGraphifyBin, isHeadAdvancing };

if (require.main === module) {
  const result = maybeGraphifyUpdate({
    toolName: process.argv[2] || 'Shell',
    command: process.argv[3] || '',
    repoRoot: process.cwd(),
  });
  process.stdout.write(JSON.stringify(result) + '\n');
}
