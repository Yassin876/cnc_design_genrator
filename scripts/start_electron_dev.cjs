const { spawn } = require('node:child_process');
const path = require('node:path');

const electronPath = require('electron');
const env = { ...process.env };

delete env.ELECTRON_RUN_AS_NODE;

const mainPath = path.join(__dirname, '..', 'electron', 'main.cjs');
const child = spawn(electronPath, [mainPath], {
  env,
  stdio: 'inherit',
  windowsHide: false,
});

child.on('error', (error) => {
  console.error('[Electron] Failed to start:', error);
  process.exit(1);
});

child.on('exit', (code, signal) => {
  if (signal) {
    console.error(`[Electron] exited with signal ${signal}`);
    process.exit(1);
  }

  process.exit(code ?? 0);
});

