<?php
/**
 * generate_form.php
 *
 * Loads the original HTML template, replaces {placeholder} tokens with
 * saved answer values, and writes the result to output/{record_id}_{safe_name}.html
 *
 * Can be included as a library (define GENERATE_FORM_LIB before including)
 * or run standalone: php generate_form.php <record_id>
 */

if (!defined('GENERATE_FORM_LIB')) {
    require_once __DIR__ . '/includes/helpers.php';
}

/**
 * Generate a filled HTML form for the given record.
 *
 * @param  int    $record_id
 * @return string  Path to the generated output file, relative to project root.
 * @throws RuntimeException on failure.
 */
function generate_form(int $record_id): string
{
    $pdo = db();

    // Load record + form info
    $record = get_record($record_id);
    if (!$record) {
        throw new RuntimeException("Record #$record_id not found.");
    }

    $form_path = __DIR__ . '/' . $record['filename'];
    if (!is_file($form_path)) {
        throw new RuntimeException("Template file not found: " . $record['filename']);
    }

    $html = file_get_contents($form_path);
    if ($html === false) {
        throw new RuntimeException("Cannot read template: " . $record['filename']);
    }

    // Load all field definitions for this form (field_key → field info)
    $fields_stmt = $pdo->prepare('SELECT * FROM form_fields WHERE form_id = ? ORDER BY display_order');
    $fields_stmt->execute([$record['form_id']]);
    $fields = $fields_stmt->fetchAll();

    // Load saved answers: field_id → value
    $values = get_record_values($record_id);

    // Build a label → value map (labels are what appear inside { } in the HTML)
    $replacements = [];
    foreach ($fields as $fld) {
        $val = $values[$fld['id']] ?? '';
        if ($val !== '') {
            // The placeholder text as it appears literally inside { }
            $replacements[$fld['field_label']] = $val;
        }
    }

    // Replace {placeholder} tokens – handle both plain text and text wrapped in <i>…</i>
    // Pattern covers: {text}, {<i>text</i>}, {<i class="…">text</i>}
    $html = preg_replace_callback(
        '/\{(<[^>]*>)?([^}]+?)(<\/[^>]*>)?\}/u',
        function (array $m) use ($replacements) {
            // $m[2] is the inner text (may contain nested HTML tags stripped)
            $inner = strip_tags($m[2]);
            $inner = html_entity_decode(trim($inner), ENT_HTML5, 'UTF-8');

            if (isset($replacements[$inner])) {
                return htmlspecialchars($replacements[$inner], ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
            }
            // Leave unfilled placeholders visually marked
            return '<span style="background:#fffacd;border:1px dashed #ccc;">{' . $m[1] . $m[2] . $m[3] . '}</span>';
        },
        $html
    );

    // ── ensure output directory exists ────────────────────────────────────
    $output_dir = __DIR__ . '/output';
    if (!is_dir($output_dir)) {
        mkdir($output_dir, 0755, true);
    }

    // Safe filename: "{record_id}_{safe_record_name}.html"
    $safe_name      = preg_replace('/[^A-Za-z0-9_\-]/', '_', $record['record_name']);
    $output_filename = $record_id . '_' . $safe_name . '.html';
    $output_path     = $output_dir . '/' . $output_filename;

    if (file_put_contents($output_path, $html) === false) {
        throw new RuntimeException("Cannot write output file: $output_path");
    }

    // Update the record row with the output filename
    $upd = db()->prepare('UPDATE form_records SET output_filename = ? WHERE id = ?');
    $upd->execute(['output/' . $output_filename, $record_id]);

    return 'output/' . $output_filename;
}

// ── Standalone CLI usage ───────────────────────────────────────────────────
if (!defined('GENERATE_FORM_LIB') && PHP_SAPI === 'cli') {
    $record_id = (int)($argv[1] ?? 0);
    if (!$record_id) {
        fwrite(STDERR, "Usage: php generate_form.php <record_id>\n");
        exit(1);
    }
    try {
        $path = generate_form($record_id);
        echo "Generated: $path\n";
    } catch (RuntimeException $e) {
        fwrite(STDERR, "Error: " . $e->getMessage() . "\n");
        exit(1);
    }
}
