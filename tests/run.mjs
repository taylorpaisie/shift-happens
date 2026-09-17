import { readFile } from 'node:fs/promises';
import { runSuite } from './suite.js';
const results = await runSuite(name => readFile(new URL(`../fixtures/${name}`, import.meta.url), 'utf8'), r => console.log(`${r.ok ? 'PASS' : 'FAIL'} ${r.name}${r.error ? ': ' + r.error : ''}`));
console.log(`${results.filter(r=>r.ok).length}/${results.length} passed`);
if (results.some(r=>!r.ok)) process.exitCode = 1;
