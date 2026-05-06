# Project rules — forms questionnaire system

This file is auto-loaded by Claude Code sessions in this repo. It captures the durable conventions and product constraints every contributor should follow. The deeper sources are:

- `SPECS.md` — product manifesto and methodology (the "why").
- `HANDOFF.md` — current engineering state and phase plan (the "where we are").
- `catalog/fields.yaml` — canonical field catalog (the "schema").

Read those before making roadmap or schema decisions.

---

## 1. Boolean-first questionnaire UX

Client-facing questions should be **yes/no wherever possible**. Decompose enums into a cascade of yes/no questions, not radio/select.

- For an enum field, generate one boolean question per option and use a `contributes:` key in the question file to map true answers back to the underlying enum/set value.
- Catalog field types stay typed (enum, set, string, etc.) — only the **question-bank presentation** is boolean-heavy.
- Keep non-decomposable inputs (names, addresses, dates, currency, county selection from 254 options) as text/date/currency/select; boolean cascades don't help there.

Why: SPECS.md "Twenty Questions" / "Directing the Inner Mind" / "Yes/No Not Maybe So" — yes/no questions direct mental flow rather than interrupt it; open-ended prompts cause stressed users to drift to general/emotional answers.

## 2. Question-bank presentation rules

Three rules for writing client-facing prompts (the question-bank YAML schema in Phase 3 must support all three):

1. **`popup:`** — when a question references a fact the average user doesn't know (e.g. "After arrest, were you taken directly to the nearest magistrate?"), the question creates an internal "what is that about?" Surface a popup/note immediately so the user reads it while curiosity is live. Reserve popups for questions whose answer the user is unlikely to know — not every question.
2. **`clarify:`** — for boolean questions whose yes/no would be genuinely misleading or contradictory, offer an optional free-text input bounded to the current issue ("Briefly explain — about this specific question only"). The exception, not the default. If you're tempted to add it everywhere, the boolean decomposition probably isn't tight enough.
3. **No adjectives in prompts** (SPECS.md line 53) — prefer concrete nouns over adjective+noun constructions. Words like "lawful", "reasonable", "proper", "valid", "timely", "material" are red flags; decompose them into the underlying yes/no test the adjective is shorthand for.

The popup goes alongside the question, not inside its text — the structural separation is what creates the "mind-reading" rapport effect.

## 3. Prospecting Tool is v1 (civil substrate, criminal as subset)

The first product is a **Prospecting Tool**: a user (court-appointed indigent defendant or civil plaintiff) completes the questionnaire; the system produces a case analysis (synopsis + issue list + implicated motions + filled-out motions) and broadcasts the report to a subscribed-lawyer panel as a paid-counsel solicitation.

**Civil ⊇ Criminal.** The 100 Texas civil forms in `forms/` are the engineering substrate. SPECS.md's arrest/magistrate examples illustrate methodology — criminal-defense intake is a content specialization on top of the same catalog/manifest/template/question-bank layers, **not** a separate stack. Don't fork schemas for criminal; extend the civil ones.

Phase 4 web-app routes serve the civil substrate; criminal-specific intake is content (additional templates + question files).

## 4. Five layers stay decoupled

```
catalog (types) ≠ question bank (UX) ≠ manifests (per-form mapping) ≠ templates (HTML) ≠ runtime (code)
```

- Changing UI wording must not touch the catalog.
- Form manifests reference stable token IDs injected into normalized templates. Never reference placeholders by raw string or by occurrence count in original HTML.
- Polymorphic placeholders (`{<i>name</i>}` appears as plaintiff, defendant, attorney, judge depending on context) get one token per occurrence; mapping each to a catalog key is a human judgment from surrounding HTML.

## 5. Companion workstreams (post-Phase 4)

Tracked but not in scope for the current phase:

- **Codes library** — seven planned modules: federal Penal Code, Code of Criminal Procedure, Rules of Civil Procedure, Rules of Evidence, Rules of Professional Conduct, Cannons of Judicial Conduct, Pattern Jury Charges. Future top-level subdirs (`codes/<area>/`). Modules 5 and 6 also auto-generate grievances and complaints, requiring additional template libraries.
- **Case-law refresh** — the 100 forms cite 2008 authority; every cited case needs a current-authority replacement. Capture cited cases as a structured layer (e.g. `data/citations.yaml`) so updates are tracked, not buried in inline template edits.
- **Briefs** — 3-page brief per legal point/issue at `briefs/<issue-slug>.md`, standardized: elements, prima facie burden, defenses, common procedural pitfalls. Referenced from analysis output so the report can hyperlink.

## 6. Tooling

- Node v20 + npm. `npm run extract`, `npm run validate`, `npm test`.
- TypeScript strict ES2022 + Node types. ESM (`"type": "module"`).
- `cheerio` for HTML, `yaml` for YAML, `zod` for runtime schema validation.
