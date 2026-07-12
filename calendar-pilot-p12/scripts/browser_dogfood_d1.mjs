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
const phases = ['before-restart', 'after-restart', 'd7-precommit', 'd7-commit', 'd7-undo'];
if (!phases.includes(mode) || !baseUrl || !runDir) {
  throw new Error(`usage: browser_dogfood_d1.mjs <${phases.join('|')}> <base-url> <run-dir>`);
}

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(await readFile(path.join(runDir, 'run_manifest.json'), 'utf8'));
if (!['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7'].includes(manifest.cell)) throw new Error(`D1-D7 browser driver cannot execute cell ${manifest.cell}`);
if (manifest.cell === 'D7' && !mode.startsWith('d7-') && mode !== 'after-restart') throw new Error(`D7 cannot execute browser phase ${mode}`);
if (manifest.cell !== 'D7' && mode.startsWith('d7-')) throw new Error(`${manifest.cell} cannot execute browser phase ${mode}`);
const scenarioSet = JSON.parse(await readFile(path.join(root, manifest.scenario_set.path), 'utf8'));
const stimuli = Object.fromEntries(scenarioSet.scenarios.map(row => [row.scenario_id, row.stimulus]));
const expectedRuntimeLabel = {
  D1: 'Fixture mode',
  D2: 'Swift IPC mode',
  D3: 'Live Codex mode',
  D4: 'Live DiffusionGemma mode',
  D5: 'Live provider mode',
  D6: 'Auto assistant',
  D7: 'Auto assistant',
}[manifest.cell];
const chromePath = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const captureDir = path.join(runDir, 'ruler_capture');
const screenshotDir = path.join(runDir, 'screenshots');
const configuredWaitMs = Number(process.env.CALENDAR_PILOT_BROWSER_WAIT_MS || 0);
const preregisteredWaitSeconds = ['D3', 'D4', 'D6', 'D7'].includes(manifest.cell)
  ? Number(scenarioSet.performance_budgets_seconds?.live_recommendation || 60)
  : Math.max(15, Number(scenarioSet.performance_budgets_seconds?.existing_plan_followup || 20));
const waitTimeoutMs = configuredWaitMs > 0 ? configuredWaitMs : preregisteredWaitSeconds * 1000;
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
    await waitFor(client, `document.querySelector("[data-testid=\\"runtime-chip\\"]")?.textContent.includes(${JSON.stringify(expectedRuntimeLabel)})`);

    if (mode === 'after-restart') {
      await record(client, 'P-RESTART', 'after_restart');
      return;
    }

    if (manifest.cell === 'D7') {
      await runD7Phase(client);
      return;
    }

    await sendStimulus(client, 'P-OBSERVE');
    await record(client, 'P-OBSERVE', 'after_observe');
    if (['D5', 'D6'].includes(manifest.cell)) await record(client, 'P-LIVE-READ', 'bounded_live_read');
    await sendStimulus(client, 'P-RECOMMEND');
    await record(client, 'P-RECOMMEND', 'after_recommend');
    await record(client, 'P-ACTION-VISIBLE', 'candidate_inspection');
    await record(client, 'P-TIMEZONE', 'timezone_inspection');
    await sendStimulus(client, 'P-FOLLOWUP');
    await record(client, 'P-FOLLOWUP', 'after_followup');

    if (await visible(client, '[data-testid="candidate-corrected"]')) {
      await click(client, '[data-testid="candidate-corrected"]');
      await waitFor(client, 'document.body.innerText.includes("Recorded corrected")');
      await sendStimulus(client, 'P-CORRECTION');
      await record(client, 'P-CORRECTION', 'after_correction', { attempted: true, succeeded: true, action: 'candidate_corrected_then_reasked' });
    } else {
      await record(client, 'P-CORRECTION', 'prerequisite_unavailable', { attempted: false, succeeded: false, reason: 'candidate_corrected_control_absent' });
    }

    if (await visible(client, '[data-testid="simulate-candidate"]')) {
      await click(client, '[data-testid="simulate-candidate"]');
      await waitFor(client, 'document.querySelectorAll("[data-testid=\\"receipt-card\\"]").length > 0');
      await record(client, 'P-SIMULATE', 'after_simulate', { attempted: true, succeeded: true, action: 'simulate' });
    } else {
      await record(client, 'P-SIMULATE', 'prerequisite_unavailable', { attempted: false, succeeded: false, reason: 'simulate_control_absent' });
    }
    if (manifest.cell !== 'D1') {
      if (await visible(client, '[data-testid="commit-candidate"]')) {
        await setAuthority(client, 0, 'recommend');
        await click(client, '[data-testid="commit-candidate"]');
        await waitFor(client, 'document.querySelector("[data-testid=\\"denial-owner\\"]") !== null');
        await record(client, 'P-DENIAL', 'after_denial', { attempted: true, succeeded: true, action: 'low_authority_commit_denied' });
        await setAuthority(client, 3, 'recommend, stage, commit_private, undo');
        if (manifest.cell === 'D2') {
          const receiptsBeforeStage = await evaluate(client, 'document.querySelectorAll("[data-testid=\\"receipt-card\\"]").length');
          await click(client, '[data-testid="stage-candidate"]');
          await waitFor(client, `document.querySelectorAll('[data-testid="receipt-card"]').length > ${receiptsBeforeStage}`);
        }
      } else {
        await record(client, 'P-DENIAL', 'prerequisite_unavailable', { attempted: false, succeeded: false, reason: 'commit_control_absent' });
      }
    }
    await sendStimulus(client, 'P-NOOP');
    if (await visible(client, '[data-testid="candidate-corrected"]')) {
      throw new Error('No-op candidate exposed an inapplicable timed-action correction control');
    }
    await record(client, 'P-NOOP', 'after_noop');
    if (await visible(client, '[data-testid="candidate-dismissed"]')) {
      await click(client, '[data-testid="candidate-dismissed"]');
      await waitFor(client, 'document.body.innerText.includes("Recorded dismissed")');
      await record(client, 'P-FEEDBACK', 'after_feedback', { attempted: true, succeeded: true, action: 'dismissed' });
    } else {
      await record(client, 'P-FEEDBACK', 'prerequisite_unavailable', { attempted: false, succeeded: false, reason: 'dismiss_control_absent' });
    }
    await record(client, 'P-RESTART', 'before_restart');
  } catch (error) {
    if (client) {
      await screenshot(client, path.join(screenshotDir, `browser-${mode}-failure.png`)).catch(() => {});
      const failureDom = await evaluate(client, 'document.documentElement.outerHTML').catch(() => '');
      if (failureDom) await writeFile(path.join(captureDir, `browser-${mode}-failure.html`), failureDom, 'utf8');
    }
    await writeFile(path.join(captureDir, `browser-${mode}-failure.txt`), `${error?.stack || error}\n`, 'utf8');
    throw error;
  } finally {
    if (client) client.close();
    await stopChrome(chrome);
    if (userDataDir) await rm(userDataDir, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 });
  }
}

async function runD7Phase(client) {
  if (mode === 'd7-precommit') {
    await sendStimulus(client, 'P-EFFECT', { requireVisibleUser: false });
    await waitFor(client, 'document.querySelector("[data-testid=\\"candidate-card\\"]") !== null');
    const view = await getJson(`${baseUrl}/api/view`);
    const candidate = view?.frontier?.candidates?.[0];
    const truth = JSON.parse(await readFile(path.join(runDir, 'operator_truth.json'), 'utf8'));
    const parent = truth.facts.find(row => row.kind === 'calendar_event')?.value || {};
    const failures = [];
    if (candidate?.intent !== 'create_prep_block') failures.push(`intent=${candidate?.intent}`);
    if ((candidate?.action?.attendees || []).length !== 0) failures.push('attendees_not_empty');
    if (candidate?.action?.calendar_id !== parent.calendar_id) failures.push(`calendar=${candidate?.action?.calendar_id}`);
    if (!String(candidate?.action?.title || '').startsWith('Prep:')) failures.push(`title=${candidate?.action?.title}`);
    if (!candidate?.candidate_id) failures.push('candidate_id_missing');
    if (failures.length) throw new Error(`D7 precommit candidate is not the exact private prep action: ${failures.join(', ')}`);
    await writeFile(path.join(runDir, 'd7_candidate.json'), `${JSON.stringify({candidate_id: candidate.candidate_id, candidate, parent_fact_id: parent.event_id}, null, 2)}\n`, 'utf8');
    await record(client, 'P-ACTION-VISIBLE', 'candidate_inspection');
    await record(client, 'P-TIMEZONE', 'timezone_inspection');
    await record(client, 'P-LIVE-READ', 'bounded_live_read');
    await click(client, `[data-testid="simulate-candidate"][data-candidate-id="${cssEscape(candidate.candidate_id)}"]`);
    await waitFor(client, 'document.querySelectorAll("[data-testid=\\"receipt-card\\"]").length > 0');
    await record(client, 'P-SIMULATE', 'after_simulate', {attempted: true, succeeded: true, action: 'simulate'});
    await setAuthority(client, 0, 'recommend');
    await click(client, `[data-testid="commit-candidate"][data-candidate-id="${cssEscape(candidate.candidate_id)}"]`);
    await waitFor(client, 'document.querySelector("[data-testid=\\"denial-owner\\"]") !== null');
    await record(client, 'P-DENIAL', 'after_denial', {attempted: true, succeeded: true, action: 'low_authority_commit_denied'});
    await setAuthority(client, 3, 'recommend, stage, commit_private, undo');
    await click(client, `[data-testid="candidate-accepted"][data-candidate-id="${cssEscape(candidate.candidate_id)}"]`);
    await waitFor(client, 'document.body.innerText.includes("Recorded accepted") || document.body.innerText.includes("Recorded useful")');
    await record(client, 'P-FEEDBACK', 'after_feedback', {attempted: true, succeeded: true, action: 'accepted'});
    return;
  }

  const bound = JSON.parse(await readFile(path.join(runDir, 'd7_candidate.json'), 'utf8'));
  if (mode === 'd7-commit') {
    await click(client, `[data-testid="commit-candidate"][data-candidate-id="${cssEscape(bound.candidate_id)}"]`);
    await waitFor(client, 'document.querySelector("[data-testid=\\"undo-action\\"]") !== null');
    await record(client, 'P-EFFECT', 'after_commit', {attempted: true, succeeded: true, action: 'confirmed_private_create', candidate_id: bound.candidate_id});
    return;
  }
  await click(client, '[data-testid="undo-action"]');
  await waitFor(client, 'Array.from(document.querySelectorAll("[data-testid=\\"receipt-card\\"]")).some(node => node.innerText.includes("reverted"))');
  await record(client, 'P-UNDO', 'after_undo', {attempted: true, succeeded: true, action: 'separately_confirmed_compensation'});
  await record(client, 'P-RESTART', 'before_restart');
}

function cssEscape(value) {
  return String(value).replaceAll('\\', '\\\\').replaceAll('"', '\\"');
}

async function setAuthority(client, tier, scopes) {
  await click(client, '[data-surface="authority"]');
  await fill(client, '#authority-tier', String(tier));
  await fill(client, '#authority-scopes', scopes);
  await click(client, '#save-authority');
  await waitFor(client, `document.querySelector('#authority-chip')?.textContent.includes('Tier ${tier}')`);
  await click(client, '[data-surface="operate"]');
}

async function sendStimulus(client, scenarioId, { requireVisibleUser = true } = {}) {
  const text = stimuli[scenarioId];
  if (!text) throw new Error(`missing frozen stimulus for ${scenarioId}`);
  const version = await evaluate(client, 'document.querySelector("#state-version")?.textContent || ""');
  await fill(client, '#goal-input', text);
  await click(client, '#send-goal');
  await waitFor(client, `document.querySelector('#state-version')?.textContent !== ${JSON.stringify(version)}`);
  if (requireVisibleUser) await waitFor(client, `Array.from(document.querySelectorAll('[data-testid="message-user"]')).some(node => node.innerText.includes(${JSON.stringify(text)}))`);
}

async function record(client, scenarioId, phase, driverInteraction = null) {
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
    driver_interaction: driverInteraction,
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

async function visible(client, selector) {
  const safe = JSON.stringify(selector);
  return Boolean(await evaluate(client, `(() => {
    const el = document.querySelector(${safe});
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && !el.disabled;
  })()`));
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
