<?php
/**
 * includes/helpers.php
 * Shared utility functions for the Texas Forms system.
 */

require_once __DIR__ . '/../config/database.php';

// ---------------------------------------------------------------------------
// Database singleton
// ---------------------------------------------------------------------------

function db(): PDO
{
    static $pdo = null;
    if ($pdo === null) {
        $dsn = sprintf(
            'mysql:host=%s;dbname=%s;charset=%s',
            DB_HOST,
            DB_NAME,
            DB_CHARSET
        );
        $options = [
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES   => false,
        ];
        $pdo = new PDO($dsn, DB_USER, DB_PASS, $options);
    }
    return $pdo;
}

// ---------------------------------------------------------------------------
// Key / label helpers
// ---------------------------------------------------------------------------

/**
 * Convert a placeholder label into a snake_case key.
 * e.g. "Name of opposing counsel" → "name_of_opposing_counsel"
 */
function sanitize_field_key(string $text): string
{
    $text = strtolower(trim($text));
    $text = preg_replace('/[^a-z0-9]+/', '_', $text);
    $text = trim($text, '_');
    // truncate to avoid overly long keys
    return substr($text, 0, 200);
}

/**
 * Extract all {placeholder} patterns from a chunk of HTML/text.
 * Returns an array of the raw inner strings (with original case).
 */
function extract_placeholders(string $html): array
{
    preg_match_all('/\{([^}]+)\}/', $html, $matches);
    return $matches[1] ?? [];
}

/**
 * Classify a placeholder label into a field type.
 */
function classify_field_type(string $label): string
{
    $upper = strtoupper($label);
    $lower = strtolower($label);

    if (str_contains($upper, 'CHOOSE') || str_contains($upper, 'ADD APPROPRIATE') || str_contains($upper, 'ADD PARAGRAPHS') || str_contains($upper, 'ADD SECTIONS')) {
        return 'choice';
    }
    if (preg_match('/\bdate\b/i', $lower)) {
        return 'date';
    }
    if (
        strlen($label) > 80
        || str_contains($lower, 'explain')
        || str_contains($lower, 'describe')
        || str_contains($lower, 'identify')
        || str_contains($lower, 'elaborate')
        || str_contains($lower, 'state ')
    ) {
        return 'textarea';
    }
    return 'text';
}

// ---------------------------------------------------------------------------
// Query helpers
// ---------------------------------------------------------------------------

function get_all_forms(): array
{
    $stmt = db()->query('SELECT * FROM forms ORDER BY form_number');
    return $stmt->fetchAll();
}

function get_form(int $form_id): array|false
{
    $stmt = db()->prepare('SELECT * FROM forms WHERE id = ?');
    $stmt->execute([$form_id]);
    return $stmt->fetch();
}

function get_form_sections(int $form_id): array
{
    $stmt = db()->prepare(
        'SELECT * FROM form_sections WHERE form_id = ? ORDER BY display_order'
    );
    $stmt->execute([$form_id]);
    return $stmt->fetchAll();
}

function get_section_fields(int $section_id): array
{
    $stmt = db()->prepare(
        'SELECT * FROM form_fields WHERE section_id = ? ORDER BY display_order'
    );
    $stmt->execute([$section_id]);
    return $stmt->fetchAll();
}

function get_form_fields_no_section(int $form_id): array
{
    $stmt = db()->prepare(
        'SELECT * FROM form_fields WHERE form_id = ? AND section_id IS NULL ORDER BY display_order'
    );
    $stmt->execute([$form_id]);
    return $stmt->fetchAll();
}

function get_all_form_fields(int $form_id): array
{
    $stmt = db()->prepare(
        'SELECT * FROM form_fields WHERE form_id = ? ORDER BY display_order'
    );
    $stmt->execute([$form_id]);
    return $stmt->fetchAll();
}

function get_record(int $record_id): array|false
{
    $stmt = db()->prepare(
        'SELECT r.*, f.title AS form_title, f.filename, f.form_number
           FROM form_records r
           JOIN forms f ON f.id = r.form_id
          WHERE r.id = ?'
    );
    $stmt->execute([$record_id]);
    return $stmt->fetch();
}

function get_record_values(int $record_id): array
{
    $stmt = db()->prepare(
        'SELECT field_id, value FROM form_record_values WHERE record_id = ?'
    );
    $stmt->execute([$record_id]);
    $rows = $stmt->fetchAll();
    $map = [];
    foreach ($rows as $row) {
        $map[$row['field_id']] = $row['value'];
    }
    return $map;
}

// ---------------------------------------------------------------------------
// HTML escaping helper
// ---------------------------------------------------------------------------

function h(string $value = ''): string
{
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
