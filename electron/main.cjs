const { app, BrowserWindow, ipcMain, dialog, shell, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
const net = require('net');
const { spawn, execSync, execFileSync } = require('child_process');

console.log('[Electron] main.cjs loaded');

function desktopLog(category, level, message, extra = {}) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] [${category}] [${level}] ${message}`);
  if (extra && Object.keys(extra).length > 0) {
    console.log(JSON.stringify(extra, null, 2));
  }
}

function configureElectronRuntime() {
  app.disableHardwareAcceleration();
  app.commandLine.appendSwitch('disable-gpu');
  app.commandLine.appendSwitch('disable-gpu-sandbox');

  if (app.isPackaged) return;

  // Suppress verbose dev-only CSP warning in development
  process.env.ELECTRON_DISABLE_SECURITY_WARNINGS = 'true';

  // Use standard Electron cache location instead of custom storage
  // This avoids permission issues with sandbox
  const appDataPath = app.getPath('userData');
  const cacheRoot = path.join(appDataPath, 'Cache');
  fs.mkdirSync(cacheRoot, { recursive: true });
  app.setPath('userData', appDataPath);
  app.setPath('cache', cacheRoot);
  // Don't set custom runtime path - use Electron defaults
}

function loadEnvFile() {
  const envPath = path.join(getProjectRoot(), '.env');
  if (!fs.existsSync(envPath)) return;

  try {
    const content = fs.readFileSync(envPath, 'utf8');
    for (const line of content.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      const eqIdx = trimmed.indexOf('=');
      if (eqIdx === -1) continue;
      const key = trimmed.slice(0, eqIdx).trim();
      let val = trimmed.slice(eqIdx + 1).trim();
      if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
        val = val.slice(1, -1);
      }
      process.env[key] = val;
    }
  } catch (err) {
    console.error('Failed to load .env file:', err);
  }
}

function getProjectRoot() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'app');
  }
  return process.cwd();
}

function getStorageRoot() {
  if (app.isPackaged) {
    return path.join(app.getPath('userData'), 'storage');
  }
  return path.join(getProjectRoot(), 'storage');
}

function ensureStorageDirectories() {
  const storageRoot = getStorageRoot();
  const uploadsDir = path.join(storageRoot, 'uploads');
  const outputsDir = path.join(storageRoot, 'outputs');
  const tempDir = path.join(storageRoot, 'temp');

  for (const dir of [uploadsDir, outputsDir, tempDir]) {
    fs.mkdirSync(dir, { recursive: true });
  }

  process.env.STORAGE_UPLOAD_DIR = uploadsDir;
  process.env.STORAGE_OUTPUT_DIR = outputsDir;
  process.env.STORAGE_TEMP_DIR = tempDir;

  desktopLog('storage', 'INFO', 'Storage directories ready', {
    root: storageRoot,
    uploads: uploadsDir,
    outputs: outputsDir,
    temp: tempDir,
  });

  return storageRoot;
}

const VITE_DEV_SERVER_URL = 'http://127.0.0.1:5173';
let mainWindow = null;
const pythonChildProcesses = [];
const backendStatus = {
  vite: { url: VITE_DEV_SERVER_URL, healthy: false },
  main_backend: { url: 'http://127.0.0.1:8000/api/v1/health', healthy: false },
  ai_server_2d: { url: 'http://127.0.0.1:8001/health', healthy: false },
  edit_server: { url: 'http://127.0.0.1:8002/health', healthy: false },
  nesting_worker: { url: 'http://127.0.0.1:8003/health', healthy: false },
  database: { healthy: false, path: null },
  checkedAt: null,
};

function resolvePythonCommand() {
  if (process.env.PYTHON_PATH && process.env.PYTHON_PATH.trim()) {
    return process.env.PYTHON_PATH.trim();
  }
  const projectPython = path.join(getProjectRoot(), '.venv', 'Scripts', 'python.exe');
  if (process.platform === 'win32' && fs.existsSync(projectPython)) {
    return projectPython;
  }
  return process.platform === 'win32' ? 'python' : 'python3';
}

function isPortInUse(port) {
  return new Promise((resolve) => {
    const socket = net.connect({ host: '127.0.0.1', port });
    socket.once('connect', () => {
      socket.destroy();
      resolve(true);
    });
    socket.once('error', () => {
      socket.destroy();
      resolve(false);
    });
  });
}

function isServiceCompatible(url, revision) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout: 3500 }, (res) => {
      let body = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => {
        try { resolve(res.statusCode === 200 && JSON.parse(body).api_revision === revision); }
        catch { resolve(false); }
      });
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => { req.destroy(); resolve(false); });
  });
}

function stopStaleUvicornOnPort(port) {
  if (process.platform === 'win32') {
    try {
      const netstatOut = execSync('netstat -ano -p tcp', { encoding: 'utf8', windowsHide: true, timeout: 3000 });
      const lines = netstatOut.split('\n');
      const pidsToKill = new Set();
      for (const line of lines) {
        if (line.includes(`:${port}`) && line.includes('LISTENING')) {
          const parts = line.trim().split(/\s+/);
          const pid = parts[parts.length - 1];
          if (pid && !isNaN(Number(pid)) && Number(pid) > 0) {
            pidsToKill.add(pid);
          }
        }
      }
      for (const pid of pidsToKill) {
        try {
          execSync(`taskkill /F /T /PID ${pid}`, { windowsHide: true, timeout: 2000, stdio: 'ignore' });
        } catch {}
      }
      return true;
    } catch (err) {
      desktopLog('services', 'WARN', 'Could not replace stale Python service', { port, message: err.message });
      return false;
    }
  } else {
    try {
      execSync(`lsof -ti:${port} | xargs kill -9`, { stdio: 'ignore', timeout: 3000 });
      return true;
    } catch {
      return false;
    }
  }
}

async function startPythonUvicornService(serviceLabel, options) {
  if (process.env.SKIP_PYTHON_SERVICES === '1') {
    desktopLog('services', 'INFO', `Skipping ${serviceLabel} (SKIP_PYTHON_SERVICES=1)`);
    return null;
  }

  const { cwd, port, modulePath, extraEnv = {} } = options;
  if (!fs.existsSync(cwd)) {
    desktopLog('services', 'WARN', `${serviceLabel} directory missing`, { path: cwd });
    return null;
  }

  // In development it is common to start the APIs separately for tests.
  // Never start a duplicate child: Windows reports that as WinError 10013.
  if (await isPortInUse(port)) {
    if (options.apiRevision && options.healthUrl && !(await isServiceCompatible(options.healthUrl, options.apiRevision))) {
      desktopLog('services', 'WARN', `${serviceLabel} is stale; replacing the old uvicorn process`, { port, expected: options.apiRevision });
      if (!stopStaleUvicornOnPort(port)) return null;
      for (let attempt = 0; attempt < 10 && await isPortInUse(port); attempt += 1) {
        await sleep(300);
      }
      if (await isPortInUse(port)) {
        desktopLog('services', 'ERROR', `${serviceLabel} port remained occupied after stale-process cleanup`, { port });
        return null;
      }
    } else {
      desktopLog('services', 'INFO', `${serviceLabel} is already listening; reusing it`, { port });
      return null;
    }
  }

  const pythonCmd = resolvePythonCommand();
  const args = ['-m', 'uvicorn', modulePath, '--host', '127.0.0.1', '--port', String(port)];
  if (!app.isPackaged && process.env.NODE_ENV !== 'production') {
    args.push('--reload');
  }

  desktopLog('services', 'INFO', `Starting ${serviceLabel}`, { port, cwd, module: modulePath });

  const child = spawn(pythonCmd, args, {
    cwd,
    env: {
      ...process.env,
      ...extraEnv,
      PYTHONUNBUFFERED: '1',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  });

  child.stdout.on('data', (chunk) => process.stdout.write(`[${serviceLabel}] ${chunk}`));
  child.stderr.on('data', (chunk) => process.stderr.write(`[${serviceLabel}] ${chunk}`));
  child.on('error', (err) => {
    desktopLog('services', 'ERROR', `${serviceLabel} process error`, { message: err.message });
  });
  child.on('exit', (code, signal) => {
    desktopLog('services', 'INFO', `${serviceLabel} exited`, { code, signal });
  });

  pythonChildProcesses.push(child);
  return child;
}

async function startAllPythonServices(projectRoot) {
  await startPythonUvicornService('main_backend', {
    cwd: projectRoot,
    port: 8000,
    modulePath: 'backend.app.main:app',
    extraEnv: { PYTHONPATH: projectRoot },
    healthUrl: 'http://127.0.0.1:8000/api/v1/health',
    apiRevision: '2d-contract-v2-paddle',
  });

  await startPythonUvicornService('ai_server_2d', {
    cwd: path.join(projectRoot, 'ai_server_2d'),
    port: 8001,
    modulePath: 'app.main:app',
    healthUrl: 'http://127.0.0.1:8001/health',
    apiRevision: '2d-contract-v2',
  });

  await startPythonUvicornService('edit_server', {
    cwd: path.join(projectRoot, 'core', 'edit_server'),
    port: 8002,
    modulePath: 'app.main:app',
  });

  await startPythonUvicornService('nesting_worker', {
    cwd: path.join(projectRoot, 'core', 'nesting_worker'),
    port: 8003,
    modulePath: 'app.main:app',
  });
}

function stopAuxiliaryPythonServices() {
  for (const proc of pythonChildProcesses) {
    try {
      if (proc && !proc.killed) proc.kill();
    } catch (err) {
      desktopLog('services', 'WARN', 'Failed to stop Python child process', { message: err.message });
    }
  }
  pythonChildProcesses.length = 0;
}

function pingHealth(url, timeoutMs = 2500) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout: timeoutMs }, (res) => {
      res.resume();
      resolve(res.statusCode >= 200 && res.statusCode < 400);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function runStartupHealthChecks(projectRoot) {
  const dbPath = path.join(projectRoot, 'cad_studio.db');
  backendStatus.database.path = dbPath;
  backendStatus.database.healthy = fs.existsSync(dbPath) || process.env.NODE_ENV === 'development';

  const maxAttempts = 3; // Reduced to 3 (4.5 seconds total)
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    backendStatus.vite.healthy = await pingHealth(VITE_DEV_SERVER_URL);
    backendStatus.main_backend.healthy = await pingHealth(backendStatus.main_backend.url);
    // Only check critical services for startup - others can start later
    backendStatus.ai_server_2d.healthy = await pingHealth(backendStatus.ai_server_2d.url);
    backendStatus.edit_server.healthy = await pingHealth(backendStatus.edit_server.url);
    backendStatus.nesting_worker.healthy = await pingHealth(backendStatus.nesting_worker.url);
    backendStatus.checkedAt = new Date().toISOString();

    const summary = Object.entries(backendStatus)
      .filter(([key]) => key !== 'checkedAt')
      .map(([key, value]) => `${key}=${value.healthy ? 'ok' : 'down'}`)
      .join(', ');

    desktopLog('health', 'INFO', `Startup health check (${attempt}/${maxAttempts}): ${summary}`);

    // Only require vite and main_backend for startup - other services can load asynchronously
    const criticalReady =
      backendStatus.vite.healthy &&
      backendStatus.main_backend.healthy;

    if (criticalReady) break;
    await sleep(1500);
  }
}

function createWindow() {
  desktopLog('lifecycle', 'INFO', 'Creating main BrowserWindow');

  const preloadPath = path.join(getProjectRoot(), 'electron', 'preload.cjs');
  const isDev = !app.isPackaged || process.env.NODE_ENV === 'development';

  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 768,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: !isDev,
      preload: preloadPath,
      webSecurity: true,
    },
    // A hidden window can remain invisible forever when a renderer import fails.
    // Show the native shell immediately and let the renderer report its own error.
    show: true,
    backgroundColor: '#0f172a',
  });

  if (isDev) {
    desktopLog('lifecycle', 'INFO', 'Loading renderer (dev mode)');
    mainWindow.loadURL(VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(path.join(getProjectRoot(), 'dist', 'index.html'));
  }

  mainWindow.once('ready-to-show', () => {
    desktopLog('lifecycle', 'INFO', 'Renderer ready to show');
    mainWindow?.show();
    mainWindow?.focus();
  });

  mainWindow.webContents.on('did-finish-load', () => {
    desktopLog('lifecycle', 'INFO', 'Renderer did-finish-load');
    mainWindow?.show();
  });

  mainWindow.webContents.on('console-message', (_event, level, message, line, sourceId) => {
    const levelName = ['verbose', 'info', 'warning', 'error'][level] || 'log';
    desktopLog('renderer', levelName.toUpperCase(), message, { line, source: sourceId });
  });

  mainWindow.webContents.on('render-process-gone', (_event, details) => {
    desktopLog('renderer', 'ERROR', 'Renderer process stopped', details);
  });

  mainWindow.webContents.on('did-fail-load', (_event, _code, _desc, validatedURL) => {
    if (isDev && validatedURL.startsWith('http://127.0.0.1:5173')) {
      desktopLog('lifecycle', 'WARN', 'Vite not ready yet — retrying in 1.5s');
      setTimeout(() => {
        if (mainWindow) mainWindow.loadURL(VITE_DEV_SERVER_URL);
      }, 1500);
    }
  });

  // A visible fallback is preferable to a silent, permanently hidden desktop app.
  setTimeout(() => {
    if (mainWindow && !mainWindow.isVisible()) {
      desktopLog('lifecycle', 'WARN', 'Renderer did not become ready in time; showing window anyway');
      mainWindow.show();
    }
  }, 5000);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function registerIPCHandlers() {
  ipcMain.handle('get-system-info', () => ({
    platform: process.platform,
    arch: process.arch,
    version: app.getVersion(),
    isPackaged: app.isPackaged,
    projectRoot: getProjectRoot(),
    storageRoot: getStorageRoot(),
  }));

  ipcMain.handle('open-external', (_event, url) => {
    shell.openExternal(url);
  });

  ipcMain.handle('show-message-box', (_event, options) => {
    return dialog.showMessageBox(mainWindow, options);
  });

  ipcMain.handle('dialog:openFile', async (_event, options = {}) => {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openFile'],
      filters: options.filters || [
        { name: 'CAD Files', extensions: ['dxf', 'stl', 'step', 'stp', 'obj', 'iges', 'igs'] },
        { name: 'All Files', extensions: ['*'] },
      ],
      ...options,
    });
    if (result.canceled || !result.filePaths.length) return null;
    return result.filePaths[0];
  });

  ipcMain.handle('dialog:saveFile', async (_event, defaultName) => {
    const result = await dialog.showSaveDialog(mainWindow, {
      defaultPath: defaultName || 'export.dxf',
      filters: [
        { name: 'DXF', extensions: ['dxf'] },
        { name: 'STL', extensions: ['stl'] },
        { name: 'All Files', extensions: ['*'] },
      ],
    });
    if (result.canceled || !result.filePath) return null;
    return result.filePath;
  });

  ipcMain.handle('app:getBackendStatus', () => backendStatus);

  ipcMain.handle('auth:googleLogin', async () => {
    const clientId = process.env.GOOGLE_CLIENT_ID;
    if (!clientId) {
      return { error: 'GOOGLE_CLIENT_ID is not configured in .env' };
    }

    return new Promise((resolve) => {
      let redirectUri = '';
      let settled = false;

      const finish = (payload) => {
        if (settled) return;
        settled = true;
        resolve(payload);
      };

      const server = http.createServer((req, res) => {
        const requestUrl = new URL(req.url, 'http://127.0.0.1');
        if (requestUrl.pathname !== '/callback') {
          res.writeHead(404);
          res.end('Not found');
          return;
        }

        const code = requestUrl.searchParams.get('code');
        const oauthError = requestUrl.searchParams.get('error');
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end('<html><body><h3>Login complete. You can close this window.</h3></body></html>');
        server.close();

        if (oauthError) {
          finish({ error: oauthError });
          return;
        }
        if (!code) {
          finish({ error: 'No authorization code received from Google.' });
          return;
        }

        finish({ code, redirect_uri: redirectUri });
      });

      server.listen(0, '127.0.0.1', () => {
        const address = server.address();
        const port = typeof address === 'object' && address ? address.port : 0;
        redirectUri = `http://127.0.0.1:${port}/callback`;
        const authUrl = new URL('https://accounts.google.com/o/oauth2/v2/auth');
        authUrl.searchParams.set('client_id', clientId);
        authUrl.searchParams.set('redirect_uri', redirectUri);
        authUrl.searchParams.set('response_type', 'code');
        authUrl.searchParams.set('scope', 'openid email profile');
        authUrl.searchParams.set('access_type', 'offline');
        authUrl.searchParams.set('prompt', 'select_account');

        shell.openExternal(authUrl.toString());

        setTimeout(() => {
          server.close();
          finish({ error: 'Google login timed out after 3 minutes.' });
        }, 180000);
      });

      server.on('error', (err) => {
        finish({ error: `Google login server error: ${err.message}` });
      });
    });
  });
}

configureElectronRuntime();
loadEnvFile();

app.whenReady().then(async () => {
  const projectRoot = getProjectRoot();
  // The default Electron File/Edit/View menu makes the renderer look like a
  // generic browser window. The CAD UI owns its actions, so keep the desktop
  // shell focused and remove the unused native menu.
  Menu.setApplicationMenu(null);
  ensureStorageDirectories();

  desktopLog('lifecycle', 'INFO', `CNC Studio Electron v${app.getVersion()} starting`, {
    platform: process.platform,
    arch: process.arch,
    electron: process.versions.electron,
    node: process.versions.node,
    packaged: app.isPackaged,
    projectRoot,
  });

  registerIPCHandlers();
  
  // Start window immediately - don't wait for services
  createWindow();
  
  // Start services in background after window is created
  startAllPythonServices(projectRoot);

  // Run health checks in background - don't block startup
  runStartupHealthChecks(projectRoot).catch((err) => {
    desktopLog('health', 'ERROR', 'Startup health checks failed', { message: err.message });
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      desktopLog('lifecycle', 'INFO', 'Re-activating — creating new window');
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  desktopLog('lifecycle', 'INFO', 'All windows closed — shutting down');
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  desktopLog('lifecycle', 'INFO', 'Application quitting');
  stopAuxiliaryPythonServices();
});
