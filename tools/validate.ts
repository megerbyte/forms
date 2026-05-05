#!/usr/bin/env tsx
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { parse } from 'yaml';

const CATALOG = 'catalog/fields.yaml';
const TEMPLATES_DIR = 'templates';
const MANIFESTS_DIR = 'manifests';

type CatalogField = {
  key: string;
  type?: string;
  item?: Array<{ key: string }>;
};

function loadCatalogKeys(): Set<string> {
  const raw = readFileSync(CATALOG, 'utf8');
  const fields = parse(raw) as CatalogField[];
  const keys = new Set<string>();
  for (const f of fields) {
    keys.add(f.key);
    if (f.type === 'list' && Array.isArray(f.item)) {
      for (const sub of f.item) {
        keys.add(`${f.key}[].${sub.key}`);
      }
    }
  }
  return keys;
}

type Manifest = {
  form_id: string;
  template: string;
  placeholders?: Array<{ token: string; raw: string; field: string; form_specific?: boolean }>;
  choices?: Array<{ token: string; raw: string; field: string; form_specific?: boolean }>;
};

function extractTemplateTokens(html: string): Set<string> {
  const tokens = new Set<string>();
  const re = /data-token="([^"]+)"/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html)) !== null) tokens.add(m[1]);
  return tokens;
}

const catalogKeys = loadCatalogKeys();
const manifestFiles = readdirSync(MANIFESTS_DIR).filter((f) => f.endsWith('.yaml')).sort();

let errors = 0;
let warnings = 0;
let todoCount = 0;
let formSpecificCount = 0;
let resolvedCount = 0;
let totalTokens = 0;

for (const mf of manifestFiles) {
  const manifest = parse(readFileSync(join(MANIFESTS_DIR, mf), 'utf8')) as Manifest;
  const allEntries = [...(manifest.placeholders ?? []), ...(manifest.choices ?? [])];

  for (const entry of allEntries) {
    totalTokens++;
    if (entry.form_specific) {
      formSpecificCount++;
      continue;
    }
    if (entry.field === 'TODO') {
      todoCount++;
      continue;
    }
    if (!catalogKeys.has(entry.field)) {
      console.error(`x ${mf}: token ${entry.token} field "${entry.field}" not in catalog`);
      errors++;
    } else {
      resolvedCount++;
    }
  }

  let templateHtml: string;
  try {
    templateHtml = readFileSync(manifest.template, 'utf8');
  } catch {
    console.error(`x ${mf}: template not found at ${manifest.template}`);
    errors++;
    continue;
  }
  const templateTokens = extractTemplateTokens(templateHtml);
  const manifestTokens = new Set(allEntries.map((e) => e.token));

  for (const t of templateTokens) {
    if (!manifestTokens.has(t)) {
      console.error(`x ${mf}: template token ${t} has no manifest entry`);
      errors++;
    }
  }
  for (const t of manifestTokens) {
    if (!templateTokens.has(t)) {
      console.warn(`! ${mf}: manifest token ${t} not in template`);
      warnings++;
    }
  }
}

console.log('--- Validation summary ---');
console.log(`Manifests:        ${manifestFiles.length}`);
console.log(`Tokens total:     ${totalTokens}`);
console.log(`  resolved:       ${resolvedCount}`);
console.log(`  TODO:           ${todoCount}`);
console.log(`  form_specific:  ${formSpecificCount}`);
console.log(`Catalog keys:     ${catalogKeys.size}`);
console.log(`Warnings:         ${warnings}`);
console.log(`Errors:           ${errors}`);

if (errors > 0) process.exit(1);
