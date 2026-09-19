// Native adapters deliberately limited to versions covered by pinned upstream fixtures.
export const SUPPORTED = Object.freeze({ FEL: ['2.00', '2.6'], MEME: ['2.1.1'] });
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
function requireValue(ok, message) { if (!ok) throw new Error(message); }
const aliases = new Map([
  ['alpha', 'alpha'], ['alpha;', 'alpha'], ['beta', 'beta'],
  ['&beta;<sup>-</sup>', 'betaMinus'], ['&beta;<sup>+</sup>', 'betaPlus'],
  ['p<sup>-</sup>', 'weightMinus'], ['p<sup>+</sup>', 'weightPlus'],
  ['LRT', 'lrt'], ['p-value', 'p'], ['Total branch length', 'branchLength'],
]);

export function validateHyPhy(raw, filename, text) {
  requireValue(object(raw) && object(raw.analysis), 'Missing analysis metadata. Only native HyPhy FEL and MEME JSON are supported; normalized project JSON is a different format.');
  const info = raw.analysis.info;
  const method = typeof info === 'string' ? /^(FEL|MEME)\s*\(/.exec(info.trim())?.[1] : undefined;
  requireValue(method, 'Unsupported analysis. Import native FEL 2.00 / 2.6 or MEME 2.1.1 JSON. Contrast-FEL and other methods are not yet validated.');
  const version = raw.analysis.version;
  requireValue(SUPPORTED[method].includes(version), `Unsupported ${method} method version ${String(version)}. Verified versions: ${SUPPORTED[method].join(', ')}. Keep the original file; request validation of a fixture for this version.`);
  requireValue(object(raw.input), 'Missing input metadata. Re-export the complete HyPhy output.');
  const length = raw.input['number of sites'];
  requireValue(Number.isInteger(length) && length > 0 && length <= 100000, 'input.number of sites must be an integer from 1 to 100000 (codons).');
  requireValue(Number.isInteger(raw.input['number of sequences']) && raw.input['number of sequences'] > 0, 'Missing or invalid input.number of sequences.');
  requireValue(raw.input['partition count'] === 1 && object(raw['data partitions']) && Object.keys(raw['data partitions']).join() === '0',
    'Only a single partition (0) is supported. Recombination partitions require separate trees and coordinate interpretation; this viewer will not flatten them. Keep the partitioned output for a recombination-aware viewer.');
  const coverage = raw['data partitions']['0']?.coverage;
  requireValue(Array.isArray(coverage) && coverage.length === 1 && Array.isArray(coverage[0]), 'Expected data partitions.0.coverage as one row of zero-based codon coordinates.');
  const coordinates = coverage[0];
  requireValue(coordinates.length > 0 && coordinates.every(c => Number.isInteger(c) && c >= 0 && c < length) && new Set(coordinates).size === coordinates.length,
    'Coverage contains duplicate, out-of-range, or invalid codon coordinates. Supply the original full-alignment coordinate mapping.');
  requireValue(object(raw.tested) && Object.keys(raw.tested).join() === '0' && object(raw.tested['0']) && Object.keys(raw.tested['0']).length > 0,
    'Missing tested.0 branch scope. Export the complete analysis; branch scope cannot be inferred from the filename.');
  requireValue(Object.values(raw.tested['0']).every(v => v === 'test' || v === 'background') && Object.values(raw.tested['0']).includes('test'), 'Unsupported tested-branch labels or no test branches. Expected test/background labels.');
  requireValue(object(raw.input.trees) && Object.keys(raw.input.trees).join() === '0' && typeof raw.input.trees['0'] === 'string' && raw.input.trees['0'].length > 0, 'Missing single-partition input tree. Export the complete HyPhy JSON.');
  requireValue(object(raw.MLE) && Array.isArray(raw.MLE.headers) && object(raw.MLE.content) && Object.keys(raw.MLE.content).join() === '0', 'Missing MLE.headers or single-partition MLE.content.0.');
  const headers = raw.MLE.headers;
  requireValue(headers.length > 0 && headers.every(h => Array.isArray(h) && h.length === 2 && h.every(v => typeof v === 'string' && v.length > 0)), 'Each MLE header must contain a name and description.');
  requireValue(new Set(headers.map(h => h[0])).size === headers.length, 'Duplicate MLE header names make the columns ambiguous.');
  // Do not accidentally discard a native correction or reinterpret an unfamiliar statistic.
  requireValue(!headers.some(h => /adjusted|corrected|q-value|false discovery|holm|bonferroni/i.test(h.join(' '))), 'This file contains correction metadata not covered by the validated adapter. Native corrections must be preserved and interpreted before this format can be supported.');
  const indexes = new Map();
  headers.forEach(([name], index) => {
    const key = aliases.get(name);
    if (key) {
      requireValue(!indexes.has(key), `Ambiguous aliases for ${key} in MLE.headers.`);
      indexes.set(key, index);
    }
  });
  const required = method === 'FEL' ? ['alpha', 'beta', 'lrt', 'p', 'branchLength'] : ['alpha', 'betaMinus', 'betaPlus', 'weightMinus', 'weightPlus', 'lrt', 'p', 'branchLength'];
  for (const key of required) requireValue(indexes.has(key), `Missing required ${method} MLE header: ${key}. Column positions are never assumed.`);
  const rows = raw.MLE.content['0'];
  requireValue(Array.isArray(rows) && rows.length === coordinates.length, 'MLE row count does not match partition coverage. The site mapping is incomplete.');
  const sites = rows.map((row, i) => {
    requireValue(Array.isArray(row) && row.length === headers.length, `MLE row ${i + 1} has the wrong number of columns. Expected ${headers.length}.`);
    const values = {};
    const issues = [];
    for (const key of required) {
      const v = row[indexes.get(key)];
      const valid = typeof v === 'number' && Number.isFinite(v) && v >= 0 && (!['p', 'weightMinus', 'weightPlus'].includes(key) || v <= 1);
      values[key] = valid ? v : null;
      if (!valid) issues.push(`${key}: missing or invalid value (original retained)`);
    }
    if (method === 'MEME' && values.weightMinus !== null && values.weightPlus !== null && Math.abs(values.weightMinus + values.weightPlus - 1) > 1e-6) issues.push('MEME mixture weights do not sum to one');
    if (values.branchLength === 0) issues.push('Zero inferred branch length: insufficient information');
    if (values.alpha === 0 && (method === 'FEL' ? values.beta === 0 : values.betaMinus === 0 && values.betaPlus === 0)) issues.push('All estimated rates are zero: insufficient information');
    return { codon: coordinates[i] + 1, partition: '0', row: i, values, issues, native: row };
  });
  return {
    method, version, length, sites, filename, synthetic: false,
    scope: method === 'FEL' ? 'Pervasive site evidence over tested branches' : 'Episodic site evidence over tested branches',
    tested: raw.tested, tree: raw.input.trees, partitions: raw['data partitions'],
    input: raw.input, analysis: raw.analysis, fits: raw.fits ?? null, timers: raw.timers ?? null,
    headers, settings: raw.settings ?? null,
    support: { field: 'p-value', correction: 'None reported in validated schema; unadjusted exploratory threshold' },
    identity: null, raw, originalText: text,
    warnings: ['Alignment identity is unavailable in this native format. This analysis is isolated; filenames, trees and sequence lengths do not establish alignment identity.',
      ...(sites.some(s => s.issues.length) ? ['Some sites have insufficient information. Inspect their original values.'] : [])],
  };
}
