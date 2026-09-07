#!/usr/bin/env node

'use strict';

const { spawnSync } = require('node:child_process');
const repoUrl = 'https://github.com/murderszn/cerberus.git';
const pythonArgs = ['-m', 'pip', 'install', 'cerberus[agent] @ git+' + repoUrl];

function commandExists(command) {
  const probe = process.platform === 'win32' ? 'where' : 'which';
  return spawnSync(probe, [command], { stdio: 'ignore' }).status === 0;
}

function run(command, args) {
  const result = spawnSync(command, args, { stdio: 'inherit', shell: false });
  if (result.error) {
    console.error(`cerberus-agent: ${result.error.message}`);
    process.exit(1);
  }
  process.exit(result.status ?? 1);
}

const args = process.argv.slice(2);
if (args.includes('--help') || args.includes('-h')) {
  console.log(`Cerberus Agent CLI launcher\n\nUsage:\n  npx cerberus-agent [cerberus arguments...]\n\nThe first run installs Cerberus into the active Python environment, then\nforwards all arguments to the Python CLI. Python 3.10+ is required.\n\nExamples:\n  npx cerberus-agent scan .\n  npx cerberus-agent agent "audit this repository"\n  npx cerberus-agent --version`);
  process.exit(0);
}

const python = commandExists('python3') ? 'python3' : (commandExists('python') ? 'python' : null);
if (!python) {
  console.error('cerberus-agent: Python 3.10+ is required. Install Python, then retry.');
  process.exit(1);
}

const versionCheck = spawnSync(python, ['-c', 'import sys; print(sys.version_info >= (3, 10))'], { encoding: 'utf8' });
if (versionCheck.status !== 0 || versionCheck.stdout.trim() !== 'True') {
  console.error('cerberus-agent: Python 3.10+ is required.');
  process.exit(1);
}

const install = spawnSync(python, pythonArgs, { stdio: 'inherit', shell: false });
if (install.status !== 0) {
  console.error('cerberus-agent: Python package installation failed.');
  process.exit(install.status ?? 1);
}

run(python, ['-m', 'servers.cli', ...args]);
