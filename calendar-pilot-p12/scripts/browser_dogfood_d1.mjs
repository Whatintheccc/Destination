#!/usr/bin/env node
/** Ruler-bound D1 browser driver. Every product interaction is a real DOM click. */
import { spawn } from 'node:child_process';
import { appendFile, mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import http from 'node:http';
import net from 'node:net';
import { fileURLToPath } from 'node:url';

const mode = process.argv[2];
const baseUrl = process.argv[3];
const runDir = process.argv[4];
if (!['before-restart', 'after-restart'].includes(mode) || !baseUrl || !runDir) {
  throw new Error('usage: browser_dogfood_d1.mjs <before-restart|after-restart> <base-url> <run-dir>');
}

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(await readFile(path.join(runDir, 'run_manifest.json'), 'utf8'));
if (manifest.cell !== 'D1') throw new Error(`D1 browser driver cannot execute cell ${manifest.cell}`);
const scenarioSet = JSON.parse(await readFile(path.join(root, manifest.scenario_set.path), 'utf8'));
const stimuli = Object.fromEntries(scenarioSet.scenarios.map(row => [row.scenario_id, row.stimulus]));
const chromePath = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const captureDir = path.join(runDir, 'ruler_capture');
const screenshotDir = path.join(runDir, 'screenshots');
const waitTimeoutMs = Number(process.env.CALENDAR_PILOT_BROWSER_WAIT_MS || 15000);
await mkdir(captureDir, { recursive: true });
await mkdir(screenshotDir, { recursive: true });

async function main() {
  let chrome;
  let client;
  let userDataDir;
  try {
    const debuggingPort = await freePort();
    userDataDir = await mkdtemp(path.join(tmpdir(), 'calendar-pilot-dogfood-chrome-'));
    chrome = spawn(chromePath, [
      '--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
      `--remote-debugging-port=${debuggingPort}`, `--user-data-dir=${userDataDir}`, 'about:blank',
    ], { stdio: ['ignore', 'ignore', 'pipe'] });
    chrome.stderr.on('data', chunk => appendFile(path.join(captureDir, 'chrome.log'), chunk));
    const target = await waitForTarget(debuggingPort);
    client = await CdpClient.connect(target.webSocketDebuggerUrl);
    await client.send('Page.enable');
    await client.send('Runtime.enable');
    await client.send('Emulation.setDeviceMetricsOverride', { width: 1360, height: 900, deviceScaleFactor: 1, mobile: false });
    await client.send('Page.navigate', { url: baseUrl });
    await waitFor(client, 'document.querySelector("[data-testid=\\"chat-transcript\\"]") !== null');
    await waitFor(client, 'document.querySelector("[data-testid=\\"runtime-chip\\"]")?.textContent.includes("Fixture mode")');

    if (mode === 'after-restart') {
      await record(client, 'P-RESTART', 'after_restart');
      return;
    }

    await sendStimulus(client, 'P-OBSERVE');
    await record(client, 'P-OBSERVE', 'after_observe');
    await sendStimulus(client, 'P-RECOMMEND');
    await record(client, 'P-RECOMMEND', 'after_recommend');
    await record(client, 'P-ACTION-VISIBLE', 'candidate_inspection');
    await record(client, 'P-TIMEZONE', 'timezone_inspection');
    await sendStimulus(client, 'P-FOLLOWUP');
    await record(client, 'P-FOLLOWUP', 'after_followup');

    await click(client, '[data-testid="candidate-corrected"]');
    await waitFor(client, 'document.body.innerText.includes("Recorded corrected")');
    await sendStimulus(client, 'P-CORRECTION');
    await record(client, 'P-CORRECTION', 'after_correction');

    await click(client, '[data-testid="simulate-candidate"]');
    await waitFor(client, 'document.querySelectorAll("[data-testid=\\"receipt-card\\"]").length > 0');
    await record(client, 'P-SIMULATE', 'after_simulate');
    await sendStimulus(client, 'P-NOOP');
    await record(client, 'P-NOOP', 'after_noop');
    await click(client, '[data-testid="candidate-dismissed"]');
    await waitFor(client, 'document.body.innerText.includes("Recorded dismissed")');
    await record(client, 'P-FEEDBACK', 'after_feedback');
    await record(client, 'P-RESTART', 'before_restart');
  } catch (error) {
    if (client) await screenshot(client, path.join(screenshotDir, `browser-${mode}-failure.png`)).catch(() => {});
    await writeFile(path.join(captureDir, `browser-${mode}-failure.txt`), `${error?.stack || error}\n`, 'utf8');
    throw error;
  } finally {
    if (client) client.close();
    await stopChrome(chrome);
    if (userDataDir) await rm(userDataDir, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 });
  }
}

async function sendStimulus(client, scenarioId) {
  const text = stimuli[scenarioId];
  if (!text) throw new Error(`missing frozen stimulus for ${scenarioId}`);
  const version = await evaluate(client, 'document.querySelector("#state-version")?.textContent || ""');
  await fill(client, '#goal-input', text);
  await click(client, '#send-goal');
  await waitFor(client, `Array.from(document.querySelectorAll('[data-testid="message-user"]')).some(node => node.innerText.includes(${JSON.stringify(text)}))`);
  await waitFor(client, `document.querySelector('#state-version')?.textContent !== ${JSON.stringify(version)}`);
}

async function record(client, scenarioId, phase) {
  const domHtml = await evaluate(client, 'document.documentElement.outerHTML');
  const view = await getJson(`${baseUrl}/api/view`);
  const replay = await getJson(`${baseUrl}/api/replay/export`);
  const health = await getJson(`${baseUrl}/api/health`);
  const sequence = (await readExistingRows()).length + 1;
  const recordId = `browser:${scenarioId}:${phase}:${sequence}`;
  const screenshotName = `${String(sequence).padStart(2, '0')}-${scenarioId.toLowerCase()}-${phase}.png`;
  const row = {
    record_id: recordId,
    run_id: manifest.run_id,
    scenario_id: scenarioId,
    phase,
    url: baseUrl,
    captured_at: new Date().toISOString(),
    dom_html: domHtml,
    view,
    replay_export: replay,
    health,
    screenshot: `screenshots/${screenshotName}`,
  };
  await appendFile(path.join(captureDir, 'browser_records.jsonl'), `${JSON.stringify(row)}\n`, 'utf8');
  await screenshot(client, path.join(screenshotDir, screenshotName));
}

async function readExistingRows() {
  try {
    return (await readFile(path.join(captureDir, 'browser_records.jsonl'), 'utf8')).split('\n').filter(Boolean);
  } catch { return []; }
}

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, response => {
      let data = '';
      response.on('data', chunk => { data += chunk; });
      response.on('end', () => {
        if (response.statusCode < 200 || response.statusCode >= 300) return reject(new Error(`${url}: HTTP ${response.statusCode}: ${data}`));
        try { resolve(JSON.parse(data)); } catch (error) { reject(error); }
      });
    }).on('error', reject);
  });
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
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
      const target = targets.find(row => row.type === 'page');
      if (target?.webSocketDebuggerUrl) return target;
    } catch (error) { lastError = error; }
    await delay(100);
  }
  throw new Error(`Chrome debugging target did not become ready: ${lastError}`);
}

class CdpClient {
  constructor(ws) {
    this.ws = ws;
    this.nextId = 1;
    this.pending = new Map();
    ws.addEventListener('message', event => {
      const message = JSON.parse(event.data);
      if (!message.id || !this.pending.has(message.id)) return;
      const callbacks = this.pending.get(message.id);
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
        if (this.pending.delete(id)) reject(new Error(`CDP timeout: ${method}`));
      }, waitTimeoutMs);
    });
  }
  close() { this.ws.close(); }
}

async function evaluate(client, expression) {
  const result = await client.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || JSON.stringify(result.exceptionDetails));
  return result.result?.value;
}

async function waitFor(client, expression) {
  const deadline = Date.now() + waitTimeoutMs;
  while (Date.now() < deadline) {
    if (await evaluate(client, `Boolean(${expression})`)) return;
    await delay(100);
  }
  throw new Error(`Timed out waiting for: ${expression}`);
}

async function click(client, selector) {
  const safe = JSON.stringify(selector);
  let info;
  const deadline = Date.now() + waitTimeoutMs;
  while (Date.now() < deadline) {
    info = await evaluate(client, `(() => {
      const el = document.querySelector(${safe});
      if (!el) return {ok:false, reason:'not_found'};
      el.scrollIntoView({block:'center'});
      const rect = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      return {ok:rect.width>0&&rect.height>0&&style.display!=='none'&&!el.disabled,x:rect.left+rect.width/2,y:rect.top+rect.height/2};
    })()`);
    if (info.ok) break;
    await delay(100);
  }
  if (!info?.ok) throw new Error(`visible element not found: ${selector}`);
  await client.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: info.x, y: info.y, button: 'none' });
  await client.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: info.x, y: info.y, button: 'left', clickCount: 1 });
  await client.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: info.x, y: info.y, button: 'left', clickCount: 1 });
}

async function fill(client, selector, value) {
  const safe = JSON.stringify(selector);
  await click(client, selector);
  await evaluate(client, `(() => { const el=document.querySelector(${safe}); el.focus(); el.value=''; el.dispatchEvent(new Event('input',{bubbles:true})); return true; })()`);
  await client.send('Input.insertText', { text: value });
  await waitFor(client, `document.querySelector(${safe})?.value === ${JSON.stringify(value)}`);
}

async function screenshot(client, filePath) {
  const result = await client.send('Page.captureScreenshot', { format: 'png', fromSurface: true });
  await writeFile(filePath, Buffer.from(result.data, 'base64'));
}

function delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

async function stopChrome(chrome) {
  if (!chrome || chrome.exitCode !== null) return;
  chrome.kill('SIGTERM');
  await Promise.race([new Promise(resolve => chrome.once('exit', resolve)), delay(3000)]);
  if (chrome.exitCode === null) chrome.kill('SIGKILL');
}

await main();
