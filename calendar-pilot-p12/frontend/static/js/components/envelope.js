import {h, clear} from '../h.js';

export function openEnvelopeOverlay(payload) {
  let overlay = document.querySelector('#envelope-overlay');
  if (!overlay) {
    overlay = h('div', {id: 'envelope-overlay', class: 'overlay closed'});
    document.body.append(overlay);
  }
  clear(overlay);
  overlay.classList.remove('closed');
  overlay.append(h('div', {class: 'overlay-panel'},
    h('div', {class: 'card-header'}, h('h2', {}, 'ActionEnvelope'), h('button', {class: 'icon-button', onclick: () => overlay.classList.add('closed')}, '×')),
    h('pre', {}, JSON.stringify(payload || {}, null, 2))));
}