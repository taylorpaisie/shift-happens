export const STATES = Object.freeze({
  purifying: { label: 'FEL · purifying', color: '#2868a5', symbol: '−' },
  pervasive: { label: 'FEL · diversifying', color: '#b24d20', symbol: '+' },
  episodic: { label: 'MEME · episodic diversification', color: '#99601a', symbol: 'E' },
  difference: { label: 'Contrast-FEL · difference (demo)', color: '#76549b', symbol: 'Δ' },
  nonsignificant: { label: 'Nonsignificant', color: '#cbd2d9', symbol: '·' },
  untested: { label: 'Untested / outside coverage', color: '#ffffff', symbol: '—' },
  insufficient: { label: 'Insufficient information', color: '#eef0f3', symbol: '?' },
});
export function classify(analysis, site, threshold = 0.05) {
  if (!Number.isFinite(threshold) || threshold <= 0 || threshold > 1) throw new Error('Threshold must be greater than 0 and at most 1.');
  if (!site) return 'untested';
  if (site.issues.length || site.values.p === null) return 'insufficient';
  const v = site.values;
  if (v.p > threshold) return 'nonsignificant';
  if (analysis.method === 'FEL') return v.beta < v.alpha ? 'purifying' : v.beta > v.alpha ? 'pervasive' : 'insufficient';
  if (analysis.method === 'MEME') return v.betaPlus > v.alpha && v.weightPlus > 0 ? 'episodic' : 'insufficient';
  return analysis.synthetic && analysis.method === 'Contrast-FEL' ? 'difference' : 'insufficient';
}
export function canLink(a, b) {
  // This increment has no trusted native alignment-provenance adapter.
  // Only built-in synthetic tracks have a shared identity established by construction.
  return a.synthetic === true && b.synthetic === true && a.identity === 'builtin-demo-v1' && b.identity === a.identity && a.length === b.length;
}
export function assertCompatible(a, b) {
  if (!canLink(a, b)) throw new Error('Cannot link: verified shared alignment identity and coordinate compatibility are required. Native files remain separate; matching names or lengths are insufficient.');
}
const siteIndexes = new WeakMap();
export function siteAt(analysis, codon) {
  if (!siteIndexes.has(analysis.sites)) siteIndexes.set(analysis.sites, new Map(analysis.sites.map(s => [s.codon, s])));
  return siteIndexes.get(analysis.sites).get(codon);
}
export function scopeSummary(analysis) {
  const labels = Object.values(analysis.tested['0']);
  return `${labels.filter(v => v === 'test').length} test / ${labels.filter(v => v === 'background').length} background branches`;
}
export function evidence(analysis, codon, threshold) {
  const site = siteAt(analysis, codon);
  return { site, state: classify(analysis, site, threshold) };
}
