import { validateHyPhy } from './validation.js';
export { SUPPORTED } from './validation.js';
export const MAX_BYTES = 25 * 1024 * 1024;

// JSON decoding is separate from the schema validator and the evidence model.
export function parseHyPhy(text, filename = 'analysis.json') {
  if (typeof text !== 'string' || new TextEncoder().encode(text).length > MAX_BYTES) {
    throw new Error('File exceeds the 25 MiB limit. Use a smaller individual analysis output.');
  }
  let raw;
  try { raw = JSON.parse(text); }
  catch { throw new Error('Invalid JSON. Upload the complete HyPhy JSON output, not a log or CSV.'); }
  return validateHyPhy(raw, filename, text);
}
