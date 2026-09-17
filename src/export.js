import { STATES, evidence, scopeSummary } from './model.js';
const xml = value => String(value).replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, '\ufffd').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' }[c]));
const csvCell = value => {
  let text = value === null || value === undefined ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value);
  // Spreadsheet formula injection also applies to uploaded filenames and metadata.
  if (/^[\s]*[=+@-]/.test(text)) text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
};
export function exportCSV(analyses, threshold) {
  const fields = ['source', 'method', 'method_version', 'synthetic', 'codon_1based', 'partition', 'source_row_0based', 'state', 'alpha', 'beta', 'beta_minus', 'beta_plus', 'weight_plus', 'group_A_rate_demo', 'group_B_rate_demo', 'LRT', 'p_value', 'threshold', 'correction', 'scope', 'tested_branches', 'issues', 'native_headers', 'native_row'];
  const rows = [fields];
  for (const a of analyses) for (let codon = 1; codon <= a.length; codon++) {
    const { site, state } = evidence(a, codon, threshold);
    const v = site?.values ?? {};
    rows.push([a.filename, a.method, a.version, a.synthetic, codon, site?.partition, site?.row, STATES[state].label, v.alpha, v.beta, v.betaMinus, v.betaPlus, v.weightPlus, v.groupA, v.groupB, v.lrt, v.p, threshold, a.support.correction, a.scope, a.tested, site?.issues, a.headers, site?.native]);
  }
  return rows.map(row => row.map(csvCell).join(',')).join('\r\n');
}
export function exportSVG(analyses, threshold, start, end) {
  const width = 1200, left = 185, plotWidth = 970, cell = plotWidth / (end - start + 1);
  const legendY = 160 + analyses.length * 64;
  const sourceLines = analyses.flatMap(a => [
    ...(`${a.method} ${a.version} • ${a.filename}`.replace(/\s/g, ' ').match(/.{1,130}/gu) ?? []),
    `${scopeSummary(a)} • Partition 0 • ${a.synthetic ? 'Synthetic shared coordinates' : 'Unverified alignment identity; isolated analysis'}`,
  ]);
  const height = legendY + 215 + sourceLines.length * 20;
  const pieces = [`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="title desc">`,
    `<title id="title">Shift Happens — selection evidence</title><desc id="desc">${xml(analyses.some(a => a.synthetic) ? 'SYNTHETIC illustration. ' : '')}Codons ${start}–${end}. Separate method-native evidence, not a combined score.</desc>`,
    `<rect width="100%" height="100%" fill="white"/><g font-family="Arial, sans-serif" fill="#172c40">`,
    `<text x="35" y="40" font-size="25" font-weight="bold">Shift Happens</text><text x="35" y="65" font-size="14">See where selection changes.</text>`,
    `<text x="35" y="92" font-size="14">${analyses.some(a => a.synthetic) ? 'SYNTHETIC ILLUSTRATION • ' : ''}Unadjusted exploratory p ≤ ${threshold} • Alignment codons ${start}–${end} (1-based)</text>`];
  pieces.push(`<metadata>${xml(JSON.stringify({ threshold, start, end, sources: analyses.map(a => ({ filename: a.filename, method: a.method, version: a.version, synthetic: a.synthetic, scope: a.scope, tested: a.tested, support: a.support, settings: a.settings, partitions: a.partitions })) }))}</metadata>`);
  for (let i = 0; i < analyses.length; i++) {
    const a = analyses[i], y = 130 + i * 64;
    pieces.push(`<text x="35" y="${y + 20}" font-size="16" font-weight="bold">${xml(a.method)}</text>`);
    for (let c = start; c <= end; c++) {
      const state = STATES[evidence(a, c, threshold).state], x = left + (c - start) * cell;
      pieces.push(`<rect x="${x}" y="${y}" width="${Math.max(0.5, cell - 1)}" height="30" fill="${state.color}" stroke="#64748b" stroke-width="0.4"><title>Codon ${c}: ${xml(state.label)}</title></rect>`);
      if (cell > 10) pieces.push(`<text x="${x + cell / 2}" y="${y + 20}" text-anchor="middle" font-size="11" fill="${['−','+','E','Δ'].includes(state.symbol) ? '#ffffff' : '#243548'}">${state.symbol}</text>`);
      if (c === start || c === end || c % Math.max(1, Math.ceil((end-start+1)/12)) === 0) pieces.push(`<text x="${x + cell/2}" y="${y+46}" text-anchor="middle" font-size="10">${c}</text>`);
    }
  }
  Object.values(STATES).forEach((s, i) => {
    const x = 35 + (i % 2) * 540, y = legendY + Math.floor(i/2) * 25;
    pieces.push(`<rect x="${x}" y="${y-12}" width="17" height="17" fill="${s.color}" stroke="#64748b"/><text x="${x+26}" y="${y+1}" font-size="13">${xml(s.symbol + '  ' + s.label)}</text>`);
  });
  let y = legendY + 116;
  for (const line of sourceLines) {
    pieces.push(`<text x="35" y="${y}" font-size="12">${xml(line)}</text>`);
    y += 20;
  }
  pieces.push(`<text x="35" y="${y+8}" font-size="12">FEL: pervasive evidence. MEME: episodic diversification. Nonsignificance is not proof of neutrality.</text>`,
    `<text x="35" y="${y+27}" font-size="12">Contrast-FEL differences do not establish positive selection or locate a shift in time. No combined confidence score.</text>`,
    `<text x="35" y="${y+46}" font-size="12">Inferred selective pressures, not measured fitness. Rate ratios are omitted; original estimates remain in the evidence table.</text>`,
    `</g></svg>`);
  return pieces.join('');
}
