import assert from 'node:assert/strict';
import { readdir, readFile } from 'node:fs/promises';
import { test } from 'node:test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const sourceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const nativeDialogPattern = /\b(?:window\s*\.\s*)?(?:alert|confirm|prompt)\s*\(/g;

async function sourceFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(entries.map(async (entry) => {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) return sourceFiles(fullPath);
    if (!/\.(?:js|jsx)$/.test(entry.name) || entry.name.endsWith('.test.js')) return [];
    return [fullPath];
  }));
  return nested.flat();
}

test('el frontend no utiliza diálogos nativos del navegador', async () => {
  const violations = [];
  for (const filePath of await sourceFiles(sourceRoot)) {
    const source = await readFile(filePath, 'utf8');
    const matches = [...source.matchAll(nativeDialogPattern)];
    if (matches.length) {
      violations.push(`${path.relative(sourceRoot, filePath)}: ${matches.length}`);
    }
  }
  assert.deepEqual(violations, [], `Diálogos nativos encontrados:\n${violations.join('\n')}`);
});
