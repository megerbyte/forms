# Session Handoff — Forms Questionnaire System

## How to resume

Start a new Claude Code session in this directory and paste this prompt:

> Read `HANDOFF.md` and continue execution. The master plan lives at `/Users/muttroyalty/.claude/plans/i-want-to-create-deep-stallman.md`. Resume from "Next action" below.

## Master plan
`/Users/muttroyalty/.claude/plans/i-want-to-create-deep-stallman.md` — five-layer architecture (catalog / question bank / form manifests / normalized templates / runtime). Approved.

## What's done

- ✅ Moved 100 form HTML files from project root into `forms/` subdirectory (via `git mv`).
- ✅ Project scaffold:
  - `package.json` — type: module, scripts for `extract`, `validate`, `test`, deps: cheerio, yaml, zod, tsx, typescript
  - `tsconfig.json` — strict ES2022 + Node types
  - `.gitignore`
  - `npm install` ran cleanly (33 packages)
  - Directories created: `catalog/ data/ manifests/ templates/ questions/ tools/ lib/ tests/`
- ✅ `catalog/fields.yaml` — v0 seed catalog written. ~30 canonical fields covering: case caption, plaintiffs (list), defendants (list), attorney, contract claim, damages (incl. boolean-decomposable exemplary basis), notice, narrative, venue, jury, certificate of conference, judge.

## What's in progress (Phase 1b)

- 🔄 `data/texas_counties.yaml` — NOT YET WRITTEN. Skipped this session (kept hitting API errors mid-list). Needs to be a YAML list of all 254 Texas counties (alphabetical). Source: any standard Texas county list. Used as `enum_source:` by `case.county`, `plaintiffs[].county`, `defendants[].county` in the catalog. Validator does not currently dereference `enum_source`, so blocking the Phase 1 pipeline is not necessary, but the file should land before any UI uses these enums.

## What's done this session (Phase 1c–1e)

- ✅ `tools/extract.ts` — built and run. 100 forms processed.
- ✅ Templates written to `templates/<form_id>.html` (100 files).
- ✅ Draft manifests written to `manifests/<form_id>.yaml` (100 files), all placeholder fields set to `TODO`.
- ✅ Coverage summary: 4,751 placeholders, 9 `CHOOSE ONE OF…` markers, 1,734 distinct raw strings. Top types: `{<i>Elaborate.</i>}` (393), `{<i>name</i>}` (217), `{<i>party</i>}` (140), `{<i>Party</i>}` (137), `{<i>adverse party</i>}` (118), `{<i>date</i>}` (105).
- ✅ `tools/validate.ts` — built and run. 0 errors, 0 warnings, 4,760 tokens (4,751 placeholders + 9 choices), all `TODO`.

## Tasks (from TaskList)

| # | Status | Task |
|---|---|---|
| 1 | ✅ completed | Phase 1a: Initialize Node/TypeScript project |
| 2 | 🔄 partial    | Phase 1b: Seed catalog ✅ / counties pending |
| 3 | ✅ completed | Phase 1c: Build extractor CLI |
| 4 | ✅ completed | Phase 1d: Run extractor against all 100 forms |
| 5 | ✅ completed | Phase 1e: Build validator CLI |

## Next action (resume here)

1. **Write `data/texas_counties.yaml`** — all 254 Texas counties as a YAML list, alphabetical. Either let a fresh session generate it, or paste a known-good list.

2. **Phase 2 — fill `field: TODO` in manifests**. Two paths:
   - Manual: human reads each manifest and assigns catalog keys based on the `raw` string + neighboring HTML.
   - Assisted: write a second extractor pass (`tools/infer.ts`) that proposes catalog keys from raw text + a small window of surrounding template HTML, leaving low-confidence matches as `TODO`.

3. **Notes for Phase 2:**
   - The catalog is small (53 keys). Many placeholders will be `form_specific: true` (e.g. one-off narrative fields). The validator already accepts `form_specific: true` as a valid escape hatch.
   - Top-frequency placeholders (`{<i>name</i>}`, `{<i>party</i>}`) are polymorphic and **must** be mapped per-occurrence by reading neighboring HTML — do not bulk-assign.

## Earlier extractor spec (kept for reference)

1. **Build `tools/extract.ts`** — DONE. Spec was:
   - Walks `forms/*.html`
   - For each form, parses placeholders matching `{<i>...</i>}` and `{_______}` (with optional whitespace, optional `<i>_______</i>` variant)
   - Assigns stable token IDs: `p001`, `p002`, … for placeholders; `c001`, `c002`, … for `CHOOSE ONE OF…` markers
   - Writes normalized template to `templates/<form_id>.html` — wraps each placeholder in `<span data-token="pNNN">{<i>name</i>}</span>` so the original literal stays visible until rendering
   - Writes draft manifest to `manifests/<form_id>.yaml`:
     ```yaml
     form_id: 2B-2
     title: "Petition — Breach of Contract"
     template: templates/2B-2.html
     placeholders:
       - token: p001
         raw: "{<i>name</i>}"
         field: TODO   # human fills in later (catalog key)
     ```
   - `form_id` derived from filename: `Form_2B-2_Petition_-_Breach_of_Contract.html` → `2B-2`. Title from rest of filename, with `_` → ` ` and `&amp;` → `&`.
   - Prints coverage summary at end: total forms, total placeholders, distinct raw placeholder strings, top 20 most-common.
   - Use `cheerio` for HTML parsing (already installed). Use `yaml` package's `stringify` for YAML output.
   - CLI entry: `npm run extract` (already wired in package.json).

3. **Run extractor on all forms** (Task #4). Sanity-check a few outputs. Iterate on extractor if any forms fail.

4. **Build `tools/validate.ts`** (Task #5). Spec:
   - Loads `catalog/fields.yaml` into a set of valid keys (including dotted list-item paths like `defendants[].name`)
   - For each `manifests/*.yaml`: every `field:` either resolves to a catalog key, equals `TODO`, or has `form_specific: true`
   - For each `templates/*.html`: every `data-token` attribute appears in the corresponding manifest's `placeholders[].token`
   - Prints summary; exits non-zero on any failure
   - CLI entry: `npm run validate`

## Then Phase 2+

- **Phase 2**: human-fill the `field: TODO` entries in manifests (or pre-fill via context inference in a follow-up extractor pass).
- **Phase 3**: write `questions/*.yaml` files (boolean-first per design preference — see project memory).
- **Phase 4**: scaffold Next.js + Prisma + SQLite web app with `/forms`, `/intake`, `/review`, `/export` routes.
- **Phase 5**: round-trip test, coverage test, catalog integrity test, end-to-end manual test.

## Key design constraints to remember

- **Boolean-first questions**: client-facing questions in `questions/*.yaml` should be yes/no wherever possible. Decompose enums into boolean cascades using a `contributes:` key. (Saved to project memory.)
- **Five layers stay decoupled**: catalog (types) ≠ question bank (UX) ≠ manifests (per-form mapping) ≠ templates (HTML) ≠ runtime (code). Changing UI wording should not touch the catalog.
- **Tokens, not ordinals**: form manifests reference stable token IDs injected into normalized templates. Never reference placeholders by their raw string or by occurrence count in original HTML.
- **Polymorphic placeholders**: `{<i>name</i>}` appears in many contexts meaning different things (plaintiff, defendant, attorney, judge). Each occurrence gets its own token; mapping to a catalog key is a human judgment from surrounding HTML context.

## Environment notes

- Node v20.20.0, npm available, no pnpm. Use `npm run …`.
- Project root: `/Users/muttroyalty/homebase/forms/`
- Git branch: `main`, clean working tree before this session started.
- macOS Darwin 24.6.0.
