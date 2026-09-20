import { gzipSync } from 'node:zlib';
import { readdir, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const assetsDirectory = resolve('dist', 'assets');
const budgets = [
  { label: 'entrada compartida', pattern: /^index-.*\.js$/, maxKiB: 55 },
  { label: 'shell autenticado', pattern: /^App-.*\.js$/, maxKiB: 50 },
  { label: 'estilos globales', pattern: /^globals-.*\.css$/, maxKiB: 85 },
  { label: 'landing', pattern: /^LandingPage-.*\.js$/, maxKiB: 16 },
  { label: 'estilos landing', pattern: /^LandingPage-.*\.css$/, maxKiB: 12 },
  { label: 'bootstrap landing', pattern: /^PublicLandingApp-.*\.js$/, maxKiB: 2 },
];

const assetNames = await readdir(assetsDirectory);
let failed = false;

for (const budget of budgets) {
  const matches = assetNames.filter((name) => budget.pattern.test(name));
  if (matches.length !== 1) {
    console.error(
      `[bundle] ${budget.label}: se esperaba 1 archivo y se encontraron ${matches.length}.`,
    );
    failed = true;
    continue;
  }

  const contents = await readFile(resolve(assetsDirectory, matches[0]));
  const gzipKiB = gzipSync(contents).byteLength / 1024;
  const status = gzipKiB <= budget.maxKiB ? 'OK' : 'EXCEDE';
  console.log(
    `[bundle] ${status} ${budget.label}: ${gzipKiB.toFixed(2)} KiB gzip / ${budget.maxKiB} KiB.`,
  );
  failed ||= gzipKiB > budget.maxKiB;
}

if (failed) {
  process.exitCode = 1;
}
