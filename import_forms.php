<?php
/**
 * import_forms.php
 *
 * CLI / web script that scans all *.html files in the repository root,
 * parses each one with DOMDocument, extracts sections & placeholder fields,
 * and populates the forms / form_sections / form_fields tables.
 *
 * Usage (CLI):  php import_forms.php
 * Usage (web):  http://localhost/import_forms.php
 *               Add ?confirm=1 to actually run; otherwise shows a dry-run preview.
 */

require_once __DIR__ . '/includes/helpers.php';

$is_cli = (PHP_SAPI === 'cli');

// ── helper: emit a line of text ────────────────────────────────────────────
function out(string $line, bool $is_cli): void
{
    echo $is_cli ? $line . "\n" : '<p>' . h($line) . '</p>';
}

// ── HTML header for web mode ────────────────────────────────────────────────
if (!$is_cli) {
    echo '<!DOCTYPE html><html><head><meta charset="utf-8">
    <title>Import Forms</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    </head><body class="container py-4">';
    echo '<h1>Import Forms</h1>';

    $confirm = isset($_GET['confirm']) && $_GET['confirm'] === '1';
    if (!$confirm) {
        echo '<div class="alert alert-warning">This will import all HTML forms into the database.
              <a href="?confirm=1" class="btn btn-primary ms-3">Run Import</a></div>';
        echo '</body></html>';
        exit;
    }
}

// ── scan root directory for HTML files ─────────────────────────────────────
$root      = __DIR__;
$htmlFiles = glob($root . '/*.html');
if (empty($htmlFiles)) {
    out('No HTML files found in ' . $root, $is_cli);
    if (!$is_cli) { echo '</body></html>'; }
    exit;
}

$totalForms    = 0;
$totalSections = 0;
$totalFields   = 0;

$pdo = db();

foreach ($htmlFiles as $filepath) {
    $filename = basename($filepath);

    // ── extract form_number and title from filename ────────────────────────
    // e.g. Form_2B-1_Petition_-_General_Form.html
    //       → number: "2B-1", title: "Petition - General Form"
    if (!preg_match('/^Form_([A-Za-z0-9]+-\d+[A-Za-z]?)_(.+)\.html$/', $filename, $fm)) {
        out("  SKIP (unrecognised filename pattern): $filename", $is_cli);
        continue;
    }
    $form_number = $fm[1];
    $form_title  = str_replace(['_', '&amp;'], [' ', '&'], $fm[2]);
    $form_title  = html_entity_decode($form_title, ENT_HTML5, 'UTF-8');

    // ── skip if already imported ────────────────────────────────────────────
    $check = $pdo->prepare('SELECT id FROM forms WHERE filename = ?');
    $check->execute([$filename]);
    if ($check->fetch()) {
        out("  SKIP (already imported): $filename", $is_cli);
        continue;
    }

    // ── load the HTML ───────────────────────────────────────────────────────
    $html = file_get_contents($filepath);
    if ($html === false) {
        out("  ERROR reading file: $filename", $is_cli);
        continue;
    }

    // ── parse with DOMDocument ─────────────────────────────────────────────
    libxml_use_internal_errors(true);
    $dom = new DOMDocument();
    $dom->loadHTML('<?xml encoding="utf-8">' . $html, LIBXML_NOWARNING | LIBXML_NOERROR);
    libxml_clear_errors();

    // ── use <title> tag for a clean title if available ────────────────────
    $titleNodes = $dom->getElementsByTagName('title');
    if ($titleNodes->length > 0) {
        $raw = trim($titleNodes->item(0)->textContent);
        // strip "Form X:Y " prefix from title tag
        $form_title = preg_replace('/^Form\s+[\dA-Z:]+\s+/i', '', $raw) ?: $form_title;
        $form_title = trim($form_title);
    }

    // ── insert into forms table ────────────────────────────────────────────
    $ins = $pdo->prepare(
        'INSERT INTO forms (form_number, title, filename) VALUES (?, ?, ?)'
    );
    $ins->execute([$form_number, $form_title, $filename]);
    $form_id = (int) $pdo->lastInsertId();
    $totalForms++;

    // ── collect all <p> elements ───────────────────────────────────────────
    $paragraphs  = $dom->getElementsByTagName('p');
    $pList       = [];
    foreach ($paragraphs as $p) {
        $pList[] = $p;
    }

    // ── identify section headings ──────────────────────────────────────────
    // Section headings are <p> elements where:
    //   1. The <p> itself has class c3 (text-decoration:underline) OR
    //   2. The <p> contains a <span class="c6"> child (also underlined), OR
    //   3. The <p> has an inline style containing "underline"
    // And the text content matches "LETTER. Title" pattern.
    $sections       = [];   // [{label, title, start_idx}]
    $sectionIdxMap  = [];   // paragraph index → section array index

    $sectionOrder = 0;
    foreach ($pList as $idx => $p) {
        $text  = trim($p->textContent);
        $class = $p->getAttribute('class');
        $style = $p->getAttribute('style');

        $isUnderlined = str_contains($class, 'c3')
                     || str_contains($style, 'underline');

        // Also detect paragraphs that contain an underlined span (class c6)
        if (!$isUnderlined) {
            foreach ($p->childNodes as $child) {
                if ($child instanceof DOMElement) {
                    $childClass = $child->getAttribute('class');
                    if (str_contains($childClass, 'c6')) {
                        $isUnderlined = true;
                        break;
                    }
                }
            }
        }

        // Normalise the text: strip placeholder { } from the title portion
        $cleanText = preg_replace('/\{[^}]*\}/', '', $text);
        $cleanText = trim($cleanText);

        // Match "A. Some Title" or "A. Some Title - Extra"
        if ($isUnderlined && preg_match('/^([A-Z])\.\s+(.+)$/', $cleanText, $sm)) {
            $sections[] = [
                'label'      => $sm[1],
                'title'      => trim($sm[2]),
                'start_idx'  => $idx,
                'order'      => $sectionOrder++,
            ];
        }
    }

    // ── insert sections into DB ────────────────────────────────────────────
    $sectionDbIds = [];
    if (!empty($sections)) {
        $insSection = $pdo->prepare(
            'INSERT INTO form_sections (form_id, section_label, section_title, display_order)
             VALUES (?, ?, ?, ?)'
        );
        foreach ($sections as $s) {
            $insSection->execute([$form_id, $s['label'], $s['title'], $s['order']]);
            $sectionDbIds[] = (int) $pdo->lastInsertId();
            $totalSections++;
        }
    } else {
        // Create a single default section
        $insSection = $pdo->prepare(
            'INSERT INTO form_sections (form_id, section_label, section_title, display_order)
             VALUES (?, NULL, ?, 0)'
        );
        $insSection->execute([$form_id, 'Form Fields']);
        $sectionDbIds[] = (int) $pdo->lastInsertId();
        $totalSections++;
    }

    // ── map each paragraph to its section ─────────────────────────────────
    // Build a paragraph→section-index lookup
    $paraToSectionIdx = [];
    $currentSectionIdx = 0;
    for ($idx = 0; $idx < count($pList); $idx++) {
        // Advance section pointer when we hit the next section heading
        if (isset($sections[$currentSectionIdx + 1])
            && $idx >= $sections[$currentSectionIdx + 1]['start_idx']) {
            $currentSectionIdx++;
        }
        $paraToSectionIdx[$idx] = $currentSectionIdx;
    }

    // ── extract fields ─────────────────────────────────────────────────────
    $insField = $pdo->prepare(
        'INSERT INTO form_fields
           (form_id, section_id, field_key, field_label, field_type, choices, is_required, display_order)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
    );

    $fieldOrder  = 0;
    $seenKeys    = [];   // deduplicate within this form

    foreach ($pList as $idx => $p) {
        $text = $p->textContent;
        $placeholders = extract_placeholders($text);
        if (empty($placeholders)) {
            continue;
        }

        // Determine section DB id for this paragraph
        $secIdx      = $paraToSectionIdx[$idx] ?? 0;
        $section_id  = $sectionDbIds[$secIdx] ?? $sectionDbIds[0];

        foreach ($placeholders as $ph) {
            $ph = trim($ph);
            if ($ph === '') {
                continue;
            }

            $field_key   = sanitize_field_key($ph);
            $field_label = $ph;
            $field_type  = classify_field_type($ph);

            // Within a single form, duplicate keys get a numeric suffix
            $base_key = $field_key;
            $counter  = 1;
            while (in_array($field_key, $seenKeys, true)) {
                $field_key = $base_key . '_' . $counter++;
            }
            $seenKeys[] = $field_key;

            $choices    = null;
            $required   = 0;

            $insField->execute([
                $form_id,
                $section_id,
                $field_key,
                $field_label,
                $field_type,
                $choices,
                $required,
                $fieldOrder++,
            ]);
            $totalFields++;
        }
    }

    out("  Imported: $filename  (sections: " . count($sections) . ", fields: $fieldOrder)", $is_cli);
}

out('', $is_cli);
out("Done. Imported $totalForms forms, $totalSections sections, $totalFields fields.", $is_cli);

if (!$is_cli) {
    echo '<div class="alert alert-success mt-3">
            Import complete: ' . (int)$totalForms . ' forms, '
                              . (int)$totalSections . ' sections, '
                              . (int)$totalFields . ' fields imported.
            <a href="questionnaire.php" class="btn btn-primary ms-3">Go to Questionnaire</a>
          </div>
          </body></html>';
}
