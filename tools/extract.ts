#!/usr/bin/env tsx
import { readFileSync, writeFileSync, readdirSync, mkdirSync, existsSync } from 'node:fs';
import { join, basename } from 'node:path';
import { stringify } from 'yaml';

const FORMS_DIR = 'forms';
const TEMPLATES_DIR = 'templates';
const MANIFESTS_DIR = 'manifests';

for (const d of [TEMPLATES_DIR, MANIFESTS_DIR]) {
  if (!existsSync(d)) mkdirSync(d, { recursive: true });
}

type Placeholder = { token: string; raw: string };
type Choice = { token: string; raw: string };

const PLACEHOLDER_RE = /\{\s*(?:<i>\s*[^{}]*?\s*<\/i>|_+)\s*\}/g;
const CHOOSE_RE = /CHOOSE\s+ONE\s+OF[^.<]*?(?=[.<]|$)/gi;

function parseFilename(filename: string): { form_id: string; title: string } {
  const stem = basename(filename, '.html');
  const m = stem.match(/^Form_([^_]+)_(.+)$/);
  if (!m) throw new Error(`Cannot parse form id from ${filename}`);
  const form_id = m[1];
  const title = m[2].replace(/_/g, ' ').replace(/&amp;/g, '&').replace(/\s+-\s+/g, ' — ');
  return { form_id, title };
}

function pad(n: number): string {
  return n.toString().padStart(3, '0');
}

function processForm(html: string): {
  template: string;
  placeholders: Placeholder[];
  choices: Choice[];
} {
  const placeholders: Placeholder[] = [];
  const choices: Choice[] = [];

  let pCount = 0;
  let cCount = 0;

  let result = html.replace(CHOOSE_RE, (match) => {
    cCount++;
    const token = `c${pad(cCount)}`;
    choices.push({ token, raw: match.trim() });
    return `<span data-token="${token}" class="choice-marker">${match}</span>`;
  });

  result = result.replace(PLACEHOLDER_RE, (match) => {
    pCount++;
    const token = `p${pad(pCount)}`;
    placeholders.push({ token, raw: match });
    return `<span data-token="${token}">${match}</span>`;
  });

  return { template: result, placeholders, choices };
}

const allRawCounts = new Map<string, number>();
let totalForms = 0;
let totalPlaceholders = 0;
let totalChoices = 0;

const files = readdirSync(FORMS_DIR).filter((f) => f.endsWith('.html')).sort();

for (const file of files) {
  const fullPath = join(FORMS_DIR, file);
  const html = readFileSync(fullPath, 'utf8');
  const { form_id, title } = parseFilename(file);
  const { template, placeholders, choices } = processForm(html);

  writeFileSync(join(TEMPLATES_DIR, `${form_id}.html`), template);

  const manifest: Record<string, unknown> = {
    form_id,
    title,
    source: `${FORMS_DIR}/${file}`,
    template: `${TEMPLATES_DIR}/${form_id}.html`,
    placeholders: placeholders.map((p) => ({ token: p.token, raw: p.raw, field: 'TODO' })),
  };
  if (choices.length > 0) {
    manifest.choices = choices.map((c) => ({ token: c.token, raw: c.raw, field: 'TODO' }));
  }

  writeFileSync(
    join(MANIFESTS_DIR, `${form_id}.yaml`),
    stringify(manifest, { lineWidth: 0 })
  );

  for (const p of placeholders) {
    allRawCounts.set(p.raw, (allRawCounts.get(p.raw) ?? 0) + 1);
  }
  totalForms++;
  totalPlaceholders += placeholders.length;
  totalChoices += choices.length;
}

const distinct = allRawCounts.size;
const top20 = [...allRawCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 20);

console.log('─── Extraction summary ───');
console.log(`Forms processed:       ${totalForms}`);
console.log(`Total placeholders:    ${totalPlaceholders}`);
console.log(`Total CHOOSE markers:  ${totalChoices}`);
console.log(`Distinct raw strings:  ${distinct}`);
console.log('\nTop 20 most-common placeholders:');
for (const [raw, count] of top20) {
  const trimmed = raw.length > 70 ? raw.slice(0, 67) + '...' : raw;
  console.log(`  ${count.toString().padStart(4)}  ${trimmed}`);
}
