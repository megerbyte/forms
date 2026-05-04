<?php
/**
 * questionnaire.php
 *
 * Multi-step form questionnaire.
 *
 * Flow:
 *   GET  ?step=0               → form selection
 *   POST step=0                → store form_id + record_name, redirect to step=1
 *   GET  ?step=N&record_id=X   → show section N fields (1-indexed)
 *   POST step=N&record_id=X    → save answers in session, redirect to next step
 *   GET  ?step=review&record_id=X → review page
 *   POST step=review&record_id=X  → delegate to save_response.php
 */

session_start();
require_once __DIR__ . '/includes/helpers.php';

$step      = $_REQUEST['step']      ?? '0';
$record_id = (int)($_REQUEST['record_id'] ?? 0);

// ── Bootstrap layout wrapper ───────────────────────────────────────────────
function page_header(string $title): void
{
    echo '<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>' . h($title) . ' – Texas Forms</title>
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
  <style>
    body { background: #f8f9fa; }
    .section-card { border-left: 4px solid #0d6efd; }
    .progress { height: 8px; }
  </style>
</head>
<body>
<nav class="navbar navbar-dark bg-primary mb-4">
  <div class="container">
    <a class="navbar-brand" href="questionnaire.php">⚖ Texas Civil Forms</a>
    <div>
      <a href="records.php" class="btn btn-outline-light btn-sm">My Records</a>
    </div>
  </div>
</nav>
<div class="container pb-5">';
}

function page_footer(): void
{
    echo '</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body></html>';
}

// ═══════════════════════════════════════════════════════════════════════════
// STEP 0 – Form selection
// ═══════════════════════════════════════════════════════════════════════════
if ($step === '0') {
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $form_id     = (int)($_POST['form_id']     ?? 0);
        $record_name = trim($_POST['record_name']  ?? '');
        if (!$form_id || !$record_name) {
            header('Location: questionnaire.php?step=0&error=1');
            exit;
        }
        // initialize session storage for this questionnaire run
        $_SESSION['qform_id']     = $form_id;
        $_SESSION['qrecord_name'] = $record_name;
        $_SESSION['qanswers']     = [];

        header('Location: questionnaire.php?step=1&form_id=' . $form_id);
        exit;
    }

    // GET – show form list
    $forms = get_all_forms();

    // Group by prefix (e.g. 1B, 2B, 3E …)
    $groups = [];
    foreach ($forms as $f) {
        preg_match('/^(\d+[A-Z]+)/i', $f['form_number'], $m);
        $prefix = $m[1] ?? 'Other';
        $groups[$prefix][] = $f;
    }
    ksort($groups);

    page_header('Select a Form');
    echo '<h2 class="mb-3">Select a Form</h2>';

    if (isset($_GET['error'])) {
        echo '<div class="alert alert-danger">Please select a form and enter a record name.</div>';
    }

    echo '<form method="post" action="questionnaire.php?step=0">
      <div class="row g-3">
        <div class="col-md-8">
          <label class="form-label fw-bold">Search / Filter</label>
          <input type="text" id="formSearch" class="form-control" placeholder="Type to search…">
        </div>
      </div>
      <div class="mt-3" id="formList">';

    foreach ($groups as $prefix => $groupForms) {
        echo '<h5 class="mt-4 text-primary">Group ' . h($prefix) . '</h5>
              <div class="list-group mb-2">';
        foreach ($groupForms as $f) {
            echo '<label class="list-group-item list-group-item-action form-item">
                    <input class="form-check-input me-2" type="radio" name="form_id" value="'
                         . (int)$f['id'] . '" required>
                    <strong>' . h($f['form_number']) . '</strong> – ' . h($f['title']) . '
                  </label>';
        }
        echo '</div>';
    }

    echo '</div><!-- #formList -->
      <div class="row g-3 mt-2">
        <div class="col-md-8">
          <label class="form-label fw-bold">Record Name <span class="text-muted">(e.g. Smith v. Jones)</span></label>
          <input type="text" name="record_name" class="form-control" required
                 placeholder="Enter a name for this record">
        </div>
      </div>
      <div class="mt-3">
        <button type="submit" class="btn btn-primary btn-lg">Start Questionnaire →</button>
      </div>
    </form>';

    // Simple JS search filter
    echo "<script>
      document.getElementById('formSearch').addEventListener('input', function() {
        var q = this.value.toLowerCase();
        document.querySelectorAll('.form-item').forEach(function(el) {
          el.style.display = el.textContent.toLowerCase().includes(q) ? '' : 'none';
        });
      });
    </script>";

    page_footer();
    exit;
}

// ═══════════════════════════════════════════════════════════════════════════
// Load form & sections for steps 1+
// ═══════════════════════════════════════════════════════════════════════════
$form_id = (int)($_SESSION['qform_id'] ?? $_GET['form_id'] ?? 0);
if (!$form_id) {
    header('Location: questionnaire.php?step=0');
    exit;
}

$form     = get_form($form_id);
$sections = get_form_sections($form_id);

// If no sections exist at all, show single default bucket
if (empty($sections)) {
    $sections = [['id' => 0, 'section_label' => null, 'section_title' => 'Form Fields', 'display_order' => 0]];
}

$totalSteps = count($sections);

// ═══════════════════════════════════════════════════════════════════════════
// REVIEW step
// ═══════════════════════════════════════════════════════════════════════════
if ($step === 'review') {
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        // Hand off to save_response.php
        $_SESSION['qsubmit'] = true;
        header('Location: save_response.php');
        exit;
    }

    page_header('Review – ' . ($form['title'] ?? ''));

    echo '<h2>Review Your Answers</h2>
          <p class="text-muted">Form: <strong>' . h($form['form_number'] . ' – ' . $form['title']) . '</strong></p>';

    $answers = $_SESSION['qanswers'] ?? [];

    foreach ($sections as $sec) {
        $fields = $sec['id'] ? get_section_fields((int)$sec['id']) : get_form_fields_no_section($form_id);
        if (empty($fields)) { continue; }

        $label = $sec['section_label'] ? $sec['section_label'] . '. ' . $sec['section_title'] : $sec['section_title'];
        echo '<div class="card section-card mb-3">
                <div class="card-header fw-bold">' . h($label) . '</div>
                <div class="card-body">
                  <dl class="row mb-0">';
        foreach ($fields as $fld) {
            $val = h($answers[$fld['id']] ?? '');
            echo '<dt class="col-sm-4">' . h($fld['field_label']) . '</dt>
                  <dd class="col-sm-8">' . ($val !== '' ? nl2br($val) : '<em class="text-muted">—</em>') . '</dd>';
        }
        echo '</dl></div></div>';
    }

    echo '<form method="post" action="questionnaire.php?step=review&form_id=' . $form_id . '">
            <a href="questionnaire.php?step=' . $totalSteps . '&form_id=' . $form_id . '"
               class="btn btn-secondary me-2">← Back</a>
            <button type="submit" class="btn btn-success btn-lg">Save &amp; Generate Document</button>
          </form>';

    page_footer();
    exit;
}

// ═══════════════════════════════════════════════════════════════════════════
// STEPS 1 … N  (section-by-section)
// ═══════════════════════════════════════════════════════════════════════════
$stepNum = (int)$step;
if ($stepNum < 1 || $stepNum > $totalSteps) {
    header('Location: questionnaire.php?step=1&form_id=' . $form_id);
    exit;
}

$sectionIndex = $stepNum - 1;
$section      = $sections[$sectionIndex];
$fields       = $section['id'] ? get_section_fields((int)$section['id']) : [];

// POST – save answers then redirect
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!isset($_SESSION['qanswers'])) {
        $_SESSION['qanswers'] = [];
    }
    foreach ($fields as $fld) {
        $key = 'field_' . $fld['id'];
        $_SESSION['qanswers'][$fld['id']] = trim($_POST[$key] ?? '');
    }
    $nextStep = $stepNum < $totalSteps ? $stepNum + 1 : 'review';
    header('Location: questionnaire.php?step=' . $nextStep . '&form_id=' . $form_id);
    exit;
}

// GET – render the section form
$answers = $_SESSION['qanswers'] ?? [];

$sectionLabel = $section['section_label']
    ? $section['section_label'] . '. ' . $section['section_title']
    : ($section['section_title'] ?? 'Form Fields');

$progress = (int)(($stepNum / $totalSteps) * 100);

page_header($sectionLabel . ' – ' . ($form['title'] ?? ''));

echo '<h4 class="text-muted mb-1">' . h($form['form_number'] . ' – ' . $form['title']) . '</h4>';

// Progress bar
echo '<div class="progress mb-2" title="Step ' . $stepNum . ' of ' . $totalSteps . '">
        <div class="progress-bar" role="progressbar" style="width:' . $progress . '%"
             aria-valuenow="' . $progress . '" aria-valuemin="0" aria-valuemax="100"></div>
      </div>
      <p class="text-muted mb-3">Step ' . $stepNum . ' of ' . $totalSteps . '</p>';

echo '<div class="card section-card mb-4">
        <div class="card-header fs-5 fw-bold">' . h($sectionLabel) . '</div>
        <div class="card-body">
          <form method="post" action="questionnaire.php?step=' . $stepNum . '&form_id=' . $form_id . '">';

if (empty($fields)) {
    echo '<p class="text-muted">No fields in this section.</p>';
} else {
    foreach ($fields as $fld) {
        $name  = 'field_' . $fld['id'];
        $val   = $answers[$fld['id']] ?? '';
        $type  = $fld['field_type'];
        $label = $fld['field_label'];
        $req   = $fld['is_required'] ? 'required' : '';

        echo '<div class="mb-3">
                <label class="form-label">' . h($label) . ($fld['is_required'] ? ' <span class="text-danger">*</span>' : '') . '</label>';

        if ($type === 'textarea') {
            echo '<textarea name="' . h($name) . '" class="form-control" rows="3" ' . $req . '>'
                 . h($val) . '</textarea>';
        } elseif ($type === 'date') {
            echo '<input type="date" name="' . h($name) . '" class="form-control" value="' . h($val) . '" ' . $req . '>';
        } elseif ($type === 'choice') {
            // Render as a select or textarea for "choose" instructions
            echo '<textarea name="' . h($name) . '" class="form-control" rows="2"
                      placeholder="Specify your choice…" ' . $req . '>'
                 . h($val) . '</textarea>
                  <div class="form-text">This is a choice/instruction field – enter the applicable option or leave blank to omit.</div>';
        } else {
            echo '<input type="text" name="' . h($name) . '" class="form-control" value="' . h($val) . '" ' . $req . '>';
        }

        echo '</div>';
    }
}

$prevStep = $stepNum > 1 ? $stepNum - 1 : '0';
$prevHref = $stepNum > 1
    ? 'questionnaire.php?step=' . $prevStep . '&form_id=' . $form_id
    : 'questionnaire.php?step=0';

echo '    <div class="d-flex gap-2">
            <a href="' . $prevHref . '" class="btn btn-secondary">← Back</a>
            <button type="submit" class="btn btn-primary">
              ' . ($stepNum < $totalSteps ? 'Next Section →' : 'Review Answers →') . '
            </button>
          </div>
        </form>
      </div>
    </div>';

page_footer();
