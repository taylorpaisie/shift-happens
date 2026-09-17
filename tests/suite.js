import { parseHyPhy } from '../src/hyphy.js';
import { classify, siteAt, canLink, assertCompatible } from '../src/model.js';
import { createDemo } from '../src/demo.js';
import { exportCSV, exportSVG } from '../src/export.js';
function assert(value, message = 'Assertion failed') { if (!value) throw new Error(message); }
function equal(a, b) { assert(Object.is(a, b), `Expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`); }
function throws(fn, match) { try { fn(); } catch (e) { assert(match.test(e.message), e.message); return; } throw new Error(`Expected error matching ${match}`); }
export async function runSuite(read, onResult = () => {}) {
  const felText = await read('CD2.FEL.json'), memeText = await read('CD2.MEME.json'), partitioned = await read('partitioned.FEL.json');
  const fel = parseHyPhy(felText, 'CD2.FEL.json'), meme = parseHyPhy(memeText, 'CD2.MEME.json');
  const modify = (fn, text = felText) => { const j = JSON.parse(text); fn(j); return parseHyPhy(JSON.stringify(j)); };
  const results = [];
  const test = async (name, fn) => { try { await fn(); results.push({name, ok:true}); } catch (e) { results.push({name, ok:false, error:e.message}); } onResult(results.at(-1)); };
  await test('Official fixtures match their recorded SHA-256 digests', async () => {
    for (const [text, expected] of [[felText, '78ce35a9e9e6e2b5c8b6d819b121406fa00d02f913f02b67c4493d78229b3fed'], [memeText, '1f4e9819cb1fcd8a833bf6ac50bfa4324345c8456c8654348447a4513f0aeb50'], [partitioned, 'c826cda4dc13d61d6e5ac2b21ead918f20cdf115cd6a2ffe60bc2d36ce0084b5']]) {
      const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
      equal(Array.from(new Uint8Array(digest), b=>b.toString(16).padStart(2,'0')).join(''), expected);
    }
  });
  await test('Pinned FEL fixture: first, selected, and last rows map to known codons', () => {
    equal(fel.method, 'FEL'); equal(fel.version, '2.00'); equal(fel.sites.length, 187);
    equal(siteAt(fel, 1).values.alpha, 0.0004001600640256103);
    equal(siteAt(fel, 9).values.p, 0.04105795180923533);
    equal(siteAt(fel, 11).values.alpha, 1.569665853806078);
    equal(siteAt(fel, 187).values.beta, 0.8185143783777495);
    equal(siteAt(fel, 187).row, 186);
  });
  await test('Pinned MEME fixture: HTML header labels and native mixture estimates', () => {
    equal(meme.version, '2.1.1'); equal(meme.sites.length, 187);
    equal(siteAt(meme, 43).values.betaPlus, 6.801478770233565);
    equal(siteAt(meme, 43).values.weightPlus, 0.1297540353909942);
    equal(siteAt(meme, 76).values.p, 0.002491251281779738);
    equal(siteAt(meme, 187).values.alpha, 2.937024731663259);
  });
  await test('Header order, not column position, determines FEL values', () => {
    const changed = modify(j => { j.MLE.headers.reverse(); j.MLE.content['0'].forEach(r => r.reverse()); });
    equal(siteAt(changed, 11).values.alpha, siteAt(fel, 11).values.alpha); equal(siteAt(changed, 9).values.p, siteAt(fel, 9).values.p);
  });
  await test('Header order, not column position, determines MEME values', () => {
    const changed = modify(j => { j.MLE.headers.reverse(); j.MLE.content['0'].forEach(r => r.reverse()); }, memeText);
    equal(siteAt(changed, 43).values.betaPlus, siteAt(meme, 43).values.betaPlus);
  });
  await test('Original text, metadata, branch scope and fit diagnostics are preserved', () => {
    equal(fel.originalText, felText); equal(fel.filename, 'CD2.FEL.json'); equal(fel.tested['0'].Pig, 'test'); assert(fel.fits['Nucleotide GTR']);
    equal(JSON.stringify(fel.raw), JSON.stringify(JSON.parse(felText))); equal(fel.identity, null);
  });
  await test('Pervasive purifying and diversifying evidence remain distinct', () => {
    equal(classify(fel, siteAt(fel, 9)), 'pervasive'); equal(classify(fel, siteAt(fel, 11)), 'purifying');
    equal(classify(fel, siteAt(fel, 1)), 'nonsignificant'); equal(classify(fel, siteAt(fel, 2)), 'insufficient');
  });
  await test('MEME support means episodic diversification, never purifying', () => {
    equal(classify(meme, siteAt(meme, 43)), 'episodic'); equal(classify(meme, siteAt(meme, 1)), 'nonsignificant');
    equal(classify(meme, siteAt(meme, 2)), 'insufficient');
  });
  await test('Threshold changes do not overwrite native p-values', () => {
    equal(classify(fel, siteAt(fel, 9), .01), 'nonsignificant'); equal(siteAt(fel, 9).values.p, 0.04105795180923533);
    for (const value of [0, -1, 2, NaN]) throws(() => classify(fel, fel.sites[0], value), /Threshold/);
  });
  await test('Sparse and reordered coverage maps source rows without inventing tested sites', () => {
    const a = modify(j => { j['data partitions']['0'].coverage = [[10, 0, 186]]; j.MLE.content['0'] = j.MLE.content['0'].slice(0, 3); });
    equal(siteAt(a, 11).row, 0); equal(siteAt(a, 1).row, 1); equal(siteAt(a, 187).row, 2); equal(classify(a, siteAt(a, 2)), 'untested');
  });
  await test('Duplicate, fractional, negative, and out-of-range coverage is rejected', () => {
    for (const c of [1, -1, .5, 187, '0', null]) throws(() => modify(j => { j['data partitions']['0'].coverage[0][0] = c; }), /Coverage/);
  });
  await test('Malformed coverage, row counts and row widths are rejected', () => {
    throws(() => modify(j => { j['data partitions']['0'].coverage = [0, 1]; }), /coverage/);
    throws(() => modify(j => { j.MLE.content['0'].pop(); }), /row count/);
    throws(() => modify(j => { j.MLE.content['0'][0].pop(); }), /columns/);
  });
  await test('Official synthetic recombination fixture is rejected, never flattened', () => { throws(() => parseHyPhy(partitioned), /Recombination/); });
  await test('Hidden additional partitions are rejected even if count says one', () => {
    throws(() => modify(j => { j.MLE.content['1'] = []; }), /single-partition/);
    throws(() => modify(j => { j['data partitions']['1'] = j['data partitions']['0']; }), /partition/);
  });
  await test('Missing values and invalid numbers are not coerced to zero', () => {
    for (const v of [null, '', '0', 'NaN', -1, 1.1, false]) {
      const a = modify(j => { j.MLE.content['0'][8][4] = v; });
      equal(siteAt(a, 9).values.p, null); equal(classify(a, siteAt(a, 9)), 'insufficient'); equal(a.raw.MLE.content['0'][8][4], v);
    }
  });
  await test('Missing rate or impossible mixture weights mean insufficient information', () => {
    const a = modify(j => { j.MLE.content['0'][42][4] = .9; }, memeText); equal(classify(a, siteAt(a, 43)), 'insufficient');
    const b = modify(j => { j.MLE.content['0'][10][0] = null; }); equal(classify(b, siteAt(b, 11)), 'insufficient');
  });
  await test('Missing and ambiguous headers have actionable errors', () => {
    throws(() => modify(j => { j.MLE.headers[0][0] = 'unknown'; }), /Missing required/);
    throws(() => modify(j => { j.MLE.headers[0] = ['alpha']; }), /description/);
    throws(() => modify(j => { j.MLE.headers[1][0] = 'alpha'; }), /Duplicate/);
    throws(() => modify(j => { j.MLE.headers[1][0] = 'alpha;'; }), /Ambiguous/);
  });
  await test('Native correction metadata is never silently discarded', () => {
    throws(() => modify(j => { j.MLE.headers[4][0] = 'Corrected P-value'; }), /correction metadata/);
  });
  await test('Unsupported versions and methods are rejected', () => {
    throws(() => modify(j => { j.analysis.version = '2.6'; }), /Unsupported FEL method version/);
    throws(() => modify(j => { j.analysis.info = 'Contrast-FEL'; }), /Unsupported analysis/);
    throws(() => parseHyPhy('{"analyses":[]}'), /normalized project JSON/);
    throws(() => parseHyPhy('not JSON'), /Invalid JSON/);
  });
  await test('Missing branch scope, invalid site counts and missing trees are rejected', () => {
    throws(() => modify(j => { delete j.tested; }), /branch scope/);
    throws(() => modify(j => { j.tested['0'].Pig = 'unknown'; }), /branch labels/);
    throws(() => modify(j => { j.input['number of sites'] = '187'; }), /number of sites/);
    throws(() => modify(j => { delete j.input.trees; }), /input tree/);
  });
  await test('Equal lengths, filenames and trees cannot establish native compatibility', () => {
    equal(canLink(fel, meme), false); equal(canLink(fel, fel), false);
    throws(() => assertCompatible(fel, meme), /verified shared alignment/);
    const a = modify(j => { j.input['file name'] = meme.input['file name']; j.input.trees = meme.input.trees; }); equal(canLink(a, meme), false);
  });
  await test('Built-in synthetic tracks link only to their own compatible coordinates', () => {
    const [a,b,c] = createDemo(); equal(canLink(a,b),true); equal(canLink(a,{...b,length:71}),false); equal(canLink(a,fel),false);
    equal(classify(c,siteAt(c,13)),'difference'); equal(classify({...c,synthetic:false},siteAt(c,13)),'insufficient');
  });
  await test('CSV includes method-native evidence, missing values, mapping and settings', () => {
    const csv = exportCSV([fel], .05); equal(csv.split('\r\n').length, 188); assert(csv.includes('0.04105795180923533')); assert(csv.includes('unadjusted exploratory')); assert(csv.includes('purifying')); assert(!csv.includes('Infinity'));
    const sparse = modify(j => { j['data partitions']['0'].coverage = [[0]]; j.MLE.content['0'] = [j.MLE.content['0'][0]]; }); assert(exportCSV([sparse], .05).includes('Untested / outside coverage'));
  });
  await test('CSV escapes formulas, quotes and metadata', () => {
    const csv = exportCSV([{...fel, filename: '=HYPERLINK("bad")'}], .05); assert(csv.includes("'=")); assert(csv.includes('""bad""'));
  });
  await test('SVG has legend, scope, threshold, coordinate window and synthetic marker', () => {
    const svg = exportSVG(createDemo(), .05, 1, 36); for (const term of ['SYNTHETIC', 'p ≤ 0.05', '1–36', 'purifying', 'Nonsignificant', 'Insufficient', 'Partition 0', 'background branches', 'not proof of neutrality']) assert(svg.includes(term), term);
  });
  await test('SVG safely escapes uploaded text', () => {
    const svg = exportSVG([{...fel,filename:'<script>alert("x")</script>&'}], .05, 1, 72); assert(!svg.includes('<script>')); assert(svg.includes('&lt;script&gt;')); assert(svg.includes('&amp;'));
  });
  return results;
}
