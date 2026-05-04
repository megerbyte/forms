<?php
/**
 * save_response.php
 *
 * Called by the questionnaire review step.  Reads session answers,
 * persists them to form_records / form_record_values, calls generate_form,
 * then redirects to records.php with a success message.
 */

session_start();
require_once __DIR__ . '/includes/helpers.php';
define('GENERATE_FORM_LIB', true);
require_once __DIR__ . '/generate_form.php';

// ── Guard: must come from questionnaire ───────────────────────────────────
if (empty($_SESSION['qsubmit']) || empty($_SESSION['qform_id'])) {
    header('Location: questionnaire.php');
    exit;
}
unset($_SESSION['qsubmit']);

$form_id     = (int)$_SESSION['qform_id'];
$record_name = trim($_SESSION['qrecord_name'] ?? '');
$answers     = $_SESSION['qanswers'] ?? [];

if (!$form_id || !$record_name) {
    header('Location: questionnaire.php?step=0&error=1');
    exit;
}

$pdo = db();

try {
    $pdo->beginTransaction();

    // ── Insert form_records row ────────────────────────────────────────────
    $ins = $pdo->prepare(
        'INSERT INTO form_records (form_id, record_name) VALUES (?, ?)'
    );
    $ins->execute([$form_id, $record_name]);
    $record_id = (int)$pdo->lastInsertId();

    // ── Upsert form_record_values ──────────────────────────────────────────
    $insVal = $pdo->prepare(
        'INSERT INTO form_record_values (record_id, field_id, value)
         VALUES (?, ?, ?)
         ON DUPLICATE KEY UPDATE value = VALUES(value)'
    );
    foreach ($answers as $field_id => $value) {
        $field_id = (int)$field_id;
        if (!$field_id) { continue; }
        $insVal->execute([$record_id, $field_id, $value]);
    }

    $pdo->commit();

    // ── Generate the filled HTML document ─────────────────────────────────
    try {
        generate_form($record_id);
    } catch (RuntimeException $ge) {
        // Non-fatal: record is saved even if generation fails
        error_log('generate_form error: ' . $ge->getMessage());
    }

    // Clear session questionnaire data
    unset(
        $_SESSION['qform_id'],
        $_SESSION['qrecord_name'],
        $_SESSION['qanswers']
    );

    header('Location: records.php?success=' . $record_id);
    exit;

} catch (Exception $e) {
    $pdo->rollBack();
    error_log('save_response error: ' . $e->getMessage());
    header('Location: questionnaire.php?step=review&error=save');
    exit;
}
