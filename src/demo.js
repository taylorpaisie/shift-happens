// Hand-authored illustrative evidence, not HyPhy output or a statistical simulation.
export function createDemo() {
  return ['FEL', 'MEME', 'Contrast-FEL'].map(method => {
    const sites = Array.from({ length: 72 }, (_, i) => {
      const codon = i + 1;
      const selected = method === 'FEL' ? codon % 7 === 0 || codon % 11 === 0 : method === 'MEME' ? codon % 9 === 0 : codon % 13 === 0;
      return { codon, partition: '0', row: i, values: {
        alpha: 1, beta: codon % 7 === 0 ? 0.15 : 1.7,
        betaMinus: 0.3, betaPlus: 3.4, weightMinus: 0.8, weightPlus: 0.2,
        p: selected ? 0.008 : 0.47, lrt: selected ? 7 : 0.5, branchLength: 2,
        ...(method === 'Contrast-FEL' ? { groupA: 0.2, groupB: selected ? 1.2 : 0.25 } : {}),
      }, issues: codon === 20 ? ['Synthetic missing estimate'] : [], native: null };
    }).filter(s => s.codon !== 31);
    return { method, version: 'illustration-v1', length: 72, sites, synthetic: true,
      filename: `SYNTHETIC-${method}`, identity: 'builtin-demo-v1',
      scope: method === 'FEL' ? 'Pervasive site evidence' : method === 'MEME' ? 'Episodic site evidence' : 'Difference between branch groups A and B; does not establish positive selection',
      tested: { '0': { 'Example A': 'test', 'Example B': 'test' } },
      partitions: { '0': { coverage: [sites.map(s => s.codon - 1)] } },
      support: { field: 'p-value', correction: 'Hand-authored unadjusted illustrative p-values' },
      warnings: ['SYNTHETIC illustration. No biological inference.'], headers: [], raw: null,
      analysis: { info: 'Hand-authored synthetic illustration; not an output fixture.' }, fits: null, input: null, settings: null,
    };
  });
}
