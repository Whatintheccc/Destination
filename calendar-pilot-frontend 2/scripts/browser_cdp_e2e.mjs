#!/usr/bin/env node
import { spawn } from 'node:child_process';
import { mkdir, mkdtemp, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import http from 'node:http';
import net from 'node:net';

const baseUrl = process.argv[2];
const artifactDir = process.argv[3];
if (!baseUrl || !artifactDir) {
  throw new Error('usage: browser_cdp_e2e.mjs <base-url> <artifact-dir>');
}

const chromePath = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
await mkdir(artifactDir, { recursive: true });

async function main() {
  let chrome;
  let client;
  try {
  const debuggingPort = await freePort();
  const userDataDir = await mkdtemp(path.join(tmpdir(), 'calendar-pilot-chrome-'));
  chrome = spawn(chromePath, [
    '--headless=new',
    '--disable-gpu',
    '--no-sandbox',
    '--hide-scrollbars',
    `--remote-debugging-port=${debuggingPort}`,
    `--user-data-dir=${userDataDir}`,
    'about:blank',
  ], { stdio: ['ignore', 'pipe', 'pipe'] });
  chrome.stdout.on('data', chunk => appendLog(chunk));
  chrome.stderr.on('data', chunk => appendLog(chunk));

  const target = await waitForTarget(debuggingPort);
  client = await CdpClient.connect(target.webSocketDebuggerUrl);
  await client.send('Page.enable');
  await client.send('Runtime.enable');
  await client.send('Page.setViewport', {}).catch(() => {});
  await client.send('Page.navigate', { url: baseUrl });
  await waitFor(client, 'document.querySelector("[data-testid=\\"chat-transcript\\"]") !== null');

  await fill(client, '#goal-input', 'Make next week less chaotic');
  await click(client, '#send-goal');
  await waitFor(client, 'document.querySelectorAll("[data-testid=\\"candidate-card\\"]").length > 0');
  await click(client, '[data-testid="stage-candidate"]');
  await waitFor(client, 'document.querySelectorAll("[data-testid=\\"receipt-card\\"]").length > 0');
  await click(client, '[data-testid="commit-candidate"]');
  await waitFor(client, 'document.querySelector("[data-testid=\\"undo-action\\"]") !== null');
  await click(client, '[data-testid="undo-action"]');
  await waitFor(client, 'document.body.innerText.includes("Undo requested")');
  await click(client, '[data-testid="feedback-useful"]');
  await waitFor(client, 'document.body.innerText.includes("Feedback captured")');

  await click(client, '#tab-replay');
  await click(client, '[data-testid="replay-export"]');
  await waitFor(client, 'document.querySelector("#replay-json")?.textContent.includes("records")');
  await waitFor(client, 'document.querySelector("#replay-json")?.textContent.includes("session_id")');

  await click(client, '#tab-profile');
  await fill(client, '#profile-correction', 'Prefer planning blocks before lunch.');
  await click(client, '#propose-profile');
  await waitFor(client, 'document.body.innerText.includes("Profile repair drafted")');
  await fill(client, '#profile-correction', 'Prefer planning blocks before lunch.');
  await click(client, '#apply-profile');
  await waitFor(client, 'document.body.innerText.includes("Profile repair applied")');

  await click(client, '#tab-authority');
  await fill(client, '#authority-tier', '0');
  await fill(client, '#authority-scopes', 'recommend, stage');
  await click(client, '#save-authority');
  await waitFor(client, 'document.querySelector("#authority-chip")?.textContent.includes("Tier 0")');

  await fill(client, '#goal-input', 'Try a low-authority commit');
  await click(client, '#send-goal');
  await waitFor(client, 'document.querySelectorAll("[data-testid=\\"candidate-card\\"]").length > 0');
  await click(client, '[data-testid="commit-candidate"]');
  await waitFor(client, 'document.querySelector(".explain-denial") !== null');
  await click(client, '.explain-denial');
  await waitFor(client, 'document.body.innerText.includes("Why Swift denied it")');

  await click(client, '#tab-self-play');
  await click(client, '[data-testid="run-self-play"]');
  await waitFor(client, 'document.body.innerText.includes("Self-play release gate")');

  await click(client, '#tab-debug');
  await click(client, '#reset-fixture');
  await waitFor(client, 'document.body.innerText.includes("Reset complete")');

  await screenshot(client, path.join(artifactDir, 'browser_success.png'));
  console.log('browser CDP e2e passed');
  } catch (error) {
    if (client) {
      await screenshot(client, path.join(artifactDir, 'browser_failure.png')).catch(() => {});
    }
    await writeFile(path.join(artifactDir, 'browser_failure.txt'), `${error?.stack || error}\n`, 'utf8');
    throw error;
  } finally {
    if (client) client.close();
    if (chrome && chrome.exitCode === null) chrome.kill('SIGTERM');
  }
}

function appendLog(chunk) {
  // Keep Chrome logs out of stdout; the Python runner records server logs.
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      const port = address.port;
      server.close(() => resolve(port));
    });
    server.on('error', reject);
  });
}

async function waitForTarget(port) {
  const deadline = Date.now() + 10000;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const targets = await getJson(`http://127.0.0.1:${port}/json/list`);
      const target = targets.find(t => t.type === 'page');
      if (target?.webSocketDebuggerUrl) return target;
    } catch (error) {
      lastError = error;
    }
    await delay(100);
  }
  throw new Error(`Chrome debugging target did not become ready: ${lastError}`);
}

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, response => {
      let data = '';
      response.on('data', chunk => { data += chunk; });
      response.on('end', () => {
        try { resolve(JSON.parse(data)); } catch (error) { reject(error); }
      });
    }).on('error', reject);
  });
}

class CdpClient {
  constructor(ws) {
    this.ws = ws;
    this.nextId = 1;
    this.pending = new Map();
    ws.addEventListener('message', event => {
      const message = JSON.parse(event.data);
      if (!message.id) return;
      const callbacks = this.pending.get(message.id);
      if (!callbacks) return;
      this.pending.delete(message.id);
      if (message.error) callbacks.reject(new Error(message.error.message || JSON.stringify(message.error)));
      else callbacks.resolve(message.result || {});
    });
  }

  static connect(url) {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(url);
      ws.addEventListener('open', () => resolve(new CdpClient(ws)));
      ws.addEventListener('error', reject);
    });
  }

  send(method, params = {}) {
    const id = this.nextId++;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`CDP timeout: ${method}`));
        }
      }, 15000);
    });
  }

  close() {
    this.ws.close();
  }
}

async function evaluate(client, expression) {
  const result = await client.send('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text || JSON.stringify(result.exceptionDetails));
  }
  return result.result?.value;
}

async function waitFor(client, expression) {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    if (await evaluate(client, `Boolean(${expression})`)) return;
    await delay(100);
  }
  throw new Error(`Timed out waiting for: ${expression}`);
}

async function click(client, selector) {
  const safe = JSON.stringify(selector);
  await waitFor(client, `(() => {
    const el = document.querySelector(${safe});
    return el && !el.disabled;
  })()`);
  await evaluate(client, `document.querySelector(${safe}).click()`);
}

async function fill(client, selector, value) {
  const safeSelector = JSON.stringify(selector);
  const safeValue = JSON.stringify(value);
  await waitFor(client, `document.querySelector(${safeSelector}) !== null`);
  await evaluate(client, `
    (() => {
      const el = document.querySelector(${safeSelector});
      el.value = ${safeValue};
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    })()
  `);
}

async function screenshot(client, filePath) {
  const result = await client.send('Page.captureScreenshot', { format: 'png', fromSurface: true });
  await writeFile(filePath, Buffer.from(result.data, 'base64'));
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

await main();
