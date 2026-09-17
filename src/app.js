import { parseHyPhy, MAX_BYTES } from './hyphy.js';
import { createDemo } from './demo.js';
import { STATES, evidence, scopeSummary, canLink } from './model.js';
import { exportCSV, exportSVG } from './export.js';
const $ = id => document.getElementById(id);
const el = (tag, text, className) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (className) n.className = className; return n; };
let analyses = createDemo(), active = analyses[0], selected = 1, start = 1;
let renderedView = null;
const threshold = () => Number($('threshold').value);
const group = () => active ? analyses.filter(a => a === active || canLink(active, a)) : [];
const end = () => active ? Math.min(active.length, start + Number($('window').value) - 1) : 0;
function message(text, error = false) { $('message').textContent = text; $('message').className = error ? 'message error' : text ? 'message' : ''; }
function download(text, name, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = el('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function activate(a) { active = a; start = 1; selected = 1; render(); }
function renderFiles() {
  $('file-count').textContent = analyses.length;
  $('file-list').replaceChildren();
  for (const a of analyses) {
    const card = el('div', undefined, `file-card ${group().includes(a) ? 'active' : ''}`);
    const open = el('button', undefined, 'file-open');
    open.append(el('strong', a.method), el('span', a.filename), el('small', a.synthetic ? 'SYNTHETIC · linked illustration' : `v${a.version} · ${a.length} codons · independent`));
    open.setAttribute('aria-pressed', String(group().includes(a))); open.onclick = () => activate(a);
    const remove = el('button', '×', 'remove'); remove.setAttribute('aria-label', `Remove ${a.filename}`);
    remove.onclick = () => { analyses = analyses.filter(x => x !== a); if (active === a) activate(analyses[0]); else render(); };
    card.append(open, remove); $('file-list').append(card);
  }
}
function renderTracks() {
  $('tracks').replaceChildren();
  for (const a of group()) {
    const row = el('div', undefined, 'track');
    const label = el('div', undefined, 'track-label'); label.append(el('strong', a.method), el('small', a.method === 'FEL' ? 'Pervasive' : a.method === 'MEME' ? 'Episodic' : 'Group difference'));
    const cells = el('div', undefined, 'cells'); cells.style.gridTemplateColumns = `repeat(${end() - start + 1}, minmax(24px, 1fr))`;
    for (let c = start; c <= end(); c++) {
      const { state } = evidence(a, c, threshold()), style = STATES[state];
      const cell = el('button', style.symbol, `codon ${state} ${c === selected ? 'selected' : ''}`);
      cell.style.setProperty('--state', style.color); cell.dataset.codon = c; cell.dataset.method = a.method;
      cell.title = `${a.method} · codon ${c} · ${style.label}`; cell.setAttribute('aria-label', cell.title); cell.setAttribute('aria-pressed', String(c === selected));
      cell.tabIndex = c === selected || (selected < start || selected > end()) && c === start ? 0 : -1;
      cell.onclick = () => { selected = c; renderTracks(); renderInspector(); $('tracks').querySelector(`[data-method="${a.method}"][data-codon="${c}"]`)?.focus(); };
      cell.onkeydown = event => {
        const move = { ArrowLeft: -1, ArrowRight: 1, Home: 1-c, End: active.length-c }[event.key];
        if (move === undefined) return;
        event.preventDefault(); selected = Math.min(active.length, Math.max(1, c + move));
        if (selected < start || selected > end()) start = Math.max(1, selected - (selected < start ? 0 : Number($('window').value)-1));
        render(); $('tracks').querySelector(`[data-method="${a.method}"][data-codon="${selected}"]`)?.focus();
      };
      const wrapper = el('div', undefined, 'codon-wrap'); wrapper.append(cell, el('span', c === start || c % 6 === 0 || c === end() ? c : '', 'coordinate')); cells.append(wrapper);
    }
    row.append(label, cells); $('tracks').append(row);
  }
}
function addPair(list, key, value) { list.append(el('dt', key), el('dd', value === null || value === undefined ? 'Not available' : String(value))); }
function details(title, data) { const d = el('details'); d.append(el('summary', title), el('pre', data === undefined || data === null ? 'Not reported' : JSON.stringify(data, null, 2))); return d; }
function renderInspector() {
  $('inspector-title').textContent = active ? `Codon ${selected}` : 'Choose an analysis'; $('inspection').replaceChildren();
  for (const a of group()) {
    const { site, state } = evidence(a, selected, threshold()), card = el('article', undefined, 'evidence-card');
    card.append(el('h3', a.method), el('p', STATES[state].label, `state-label ${state}`), el('p', a.scope, 'hint'));
    const list = el('dl');
    addPair(list, 'p-value (unadjusted)', site?.values.p); addPair(list, 'Synonymous rate α', site?.values.alpha);
    if (a.method === 'FEL') addPair(list, 'Nonsynonymous rate β', site?.values.beta);
    if (a.method === 'MEME') { addPair(list, 'Nonsynonymous rate β−', site?.values.betaMinus); addPair(list, 'Nonsynonymous rate β+', site?.values.betaPlus); addPair(list, 'Mixture weight p+', site?.values.weightPlus); }
    if (a.method === 'Contrast-FEL') { addPair(list, 'Group A rate (synthetic)', site?.values.groupA); addPair(list, 'Group B rate (synthetic)', site?.values.groupB); }
    addPair(list, 'Likelihood ratio statistic', site?.values.lrt); addPair(list, 'Inferred branch length', site?.values.branchLength);
    addPair(list, 'Tested scope', scopeSummary(a)); addPair(list, 'Source', a.filename); addPair(list, 'Method version', a.version);
    addPair(list, 'Mapping', site ? `Partition ${site.partition}, source row ${site.row} → codon ${site.codon}` : 'Outside this file’s covered sites');
    card.append(list, el('p', a.support.correction, 'hint'), el('p', 'Rate ratios are not displayed: zero or poorly estimated synonymous rates can make dN/dS misleading.', 'hint'));
    if (site?.issues.length) card.append(el('p', site.issues.join('; '), 'warning'));
    for (const warning of a.warnings) card.append(el('p', warning, 'hint'));
    card.append(details('Tested branches & input tree', { tested: a.tested, trees: a.tree }), details('Source metadata & analysis settings', { analysis: a.analysis, input: a.input, settings: a.settings, partitions: a.partitions }), details('Available model fits & timings', { fits: a.fits, timers: a.timers }), details('Original site values & column definitions', { headers: a.headers, row: site?.native }));
    if (a.originalText) { const b = el('button', 'Download original JSON'); b.onclick = () => download(a.originalText, a.filename, 'application/json'); card.append(b); }
    $('inspection').append(card);
  }
}
function render() {
  renderFiles();
  $('context').textContent = !active ? 'Import an analysis or open the synthetic example to begin.' : active.synthetic ? 'SYNTHETIC EXAMPLE · Hand-authored illustration, not biological results. These three tracks share synthetic coordinates.' : `${active.filename} · Independent native analysis. Alignment identity is not verified; cross-file linking is disabled.`;
  $('context').classList.toggle('synthetic', Boolean(active?.synthetic));
  $('range').textContent = active ? `Codons ${start}–${end()} of ${active.length}` : 'No analysis';
  $('start').value = start; $('start').max = active?.length ?? 1;
  for (const id of ['csv', 'svg', 'start', 'window', 'threshold']) $(id).disabled = !active;
  $('previous').disabled = !active || start === 1; $('next').disabled = !active || end() === active.length;
  renderTracks(); renderInspector();
  if (!renderedView || renderedView.active !== active || renderedView.start !== start || renderedView.size !== $('window').value) $('tracks').scrollLeft = 0;
  renderedView = { active, start, size: $('window').value };
}
$('upload').onchange = async event => {
  const files = Array.from(event.target.files); const errors = []; let imported = 0;
  for (const file of files) {
    try {
      if (file.size > MAX_BYTES) throw new Error('File exceeds the 25 MiB limit.');
      const a = parseHyPhy(await file.text(), file.name); analyses.push(a); active = a; imported++;
    } catch (error) { errors.push(`${file.name}: ${error.message}`); }
  }
  start = 1; selected = 1; render(); event.target.value = '';
  message([imported ? `Imported ${imported} analysis file(s). Native files remain independent because shared alignment identity is not available.` : '', ...errors].filter(Boolean).join('\n'), errors.length > 0);
};
$('demo').onclick = () => { const existing = analyses.find(a => a.synthetic); if (existing) activate(existing); else { const demo = createDemo(); analyses.push(...demo); activate(demo[0]); } message('Synthetic example opened. Native imports are retained in the analysis list.'); };
$('threshold').onchange = render;
$('window').onchange = render;
$('start').onchange = () => { const value = Number($('start').value); if (!Number.isInteger(value) || value < 1 || value > active.length) { message(`Enter a codon from 1 to ${active.length}.`, true); $('start').value = start; return; } start = value; selected = start; message(''); render(); };
$('previous').onclick = () => { start = Math.max(1, start-Number($('window').value)); selected = start; render(); };
$('next').onclick = () => { start = end()+1; selected = start; render(); };
$('csv').onclick = () => download(exportCSV(group(), threshold()), active.synthetic ? 'shift-happens-SYNTHETIC.csv' : 'shift-happens-evidence.csv', 'text/csv;charset=utf-8');
$('svg').onclick = () => download(exportSVG(group(), threshold(), start, end()), active.synthetic ? 'shift-happens-SYNTHETIC.svg' : 'shift-happens-figure.svg', 'image/svg+xml');
for (const s of Object.values(STATES)) { const item = el('span'); const swatch = el('span', s.symbol, 'swatch'); swatch.style.backgroundColor = s.color; swatch.style.color = ['−','+','E','Δ'].includes(s.symbol) ? 'white' : '#192b3e'; item.append(swatch, document.createTextNode(s.label)); $('legend').append(item); }
render();
