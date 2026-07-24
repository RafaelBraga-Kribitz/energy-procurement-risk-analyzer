#!/usr/bin/env node
// run-graphify-rebuild.js — detached graphify update + copy into .planning/graphs/
// Args: <STATUS_FILE> <LOCK_FILE> <HEAD_SHA> <MS_START> <GRAPHIFY_BIN> <REPO_ROOT>

'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const [statusFile, lockFile, headSha, msStart, graphifyBin, repoRoot] = process.argv.slice(2);

function cleanup() {
  try { fs.unlinkSync(lockFile); } catch { /* ignore */ }
}

try {
  fs.writeFileSync(lockFile, String(process.pid) + '\n');
} catch { /* ignore */ }

process.on('exit', cleanup);

let exitCode = 1;
try {
  const result = spawnSync(graphifyBin, ['update', '.'], {
    cwd: repoRoot,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
    timeout: 300000,
    windowsHide: true,
    env: { ...process.env, PATH: `${path.dirname(graphifyBin)}${path.delimiter}${process.env.PATH || ''}` },
  });
  exitCode = result.status == null ? 1 : result.status;

  const outGraph = path.join(repoRoot, 'graphify-out', 'graph.json');
  const graphsDir = path.join(repoRoot, '.planning', 'graphs');
  if (exitCode === 0 && fs.existsSync(outGraph)) {
    fs.mkdirSync(graphsDir, { recursive: true });
    fs.copyFileSync(outGraph, path.join(graphsDir, 'graph.json'));
    const html = path.join(repoRoot, 'graphify-out', 'graph.html');
    const report = path.join(repoRoot, 'graphify-out', 'GRAPH_REPORT.md');
    if (fs.existsSync(html)) fs.copyFileSync(html, path.join(graphsDir, 'graph.html'));
    if (fs.existsSync(report)) fs.copyFileSync(report, path.join(graphsDir, 'GRAPH_REPORT.md'));
    try {
      fs.copyFileSync(path.join(graphsDir, 'graph.json'), path.join(graphsDir, '.last-build-snapshot.json'));
    } catch { /* ignore */ }
  }
} catch {
  exitCode = 1;
}

const duration = Date.now() - (parseInt(msStart, 10) || Date.now());
const status = {
  ts: new Date().toISOString(),
  status: exitCode === 0 ? 'ok' : 'failed',
  exit_code: exitCode,
  duration_ms: duration,
  head_at_build: headSha || null,
  graphify_version: null,
};
try {
  fs.writeFileSync(statusFile, JSON.stringify(status, null, 2) + '\n');
} catch { /* ignore */ }

cleanup();
process.exit(0);
