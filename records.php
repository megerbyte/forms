<?php
/**
 * records.php
 *
 * Manage saved form records: view, download, delete.
 */

session_start();
require_once __DIR__ . '/includes/helpers.php';
define('GENERATE_FORM_LIB', true);
require_once __DIR__ . '/generate_form.php';

$pdo = db();

// ── Actions ────────────────────────────────────────────────────────────────
$action    = $_GET['action']    ?? '';
$record_id = (int)($_GET['id']  ?? 0);

if ($action === 'delete' && $record_id) {
    $del = $pdo->prepare('DELETE FROM form_records WHERE id = ?');
    $del->execute([$record_id]);
    header('Location: records.php?deleted=1');
    exit;
}

if ($action === 'regenerate' && $record_id) {
    try {
        generate_form($record_id);
        header('Location: records.php?regenerated=1');
    } catch (RuntimeException $e) {
        header('Location: records.php?regen_error=' . urlencode($e->getMessage()));
    }
    exit;
}

// ── Fetch records ──────────────────────────────────────────────────────────
$search = trim($_GET['q'] ?? '');
if ($search !== '') {
    $stmt = $pdo->prepare(
        'SELECT r.*, f.title AS form_title, f.form_number
           FROM form_records r
           JOIN forms f ON f.id = r.form_id
          WHERE r.record_name LIKE ? OR f.title LIKE ?
          ORDER BY r.created_at DESC'
    );
    $like = '%' . $search . '%';
    $stmt->execute([$like, $like]);
} else {
    $stmt = $pdo->query(
        'SELECT r.*, f.title AS form_title, f.form_number
           FROM form_records r
           JOIN forms f ON f.id = r.form_id
          ORDER BY r.created_at DESC'
    );
}
$records = $stmt->fetchAll();

// ── HTML ───────────────────────────────────────────────────────────────────
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>My Records – Texas Forms</title>
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body>
<nav class="navbar navbar-dark bg-primary mb-4">
  <div class="container">
    <a class="navbar-brand" href="questionnaire.php">⚖ Texas Civil Forms</a>
    <a href="questionnaire.php" class="btn btn-outline-light btn-sm">New Record</a>
  </div>
</nav>
<div class="container pb-5">
  <h2 class="mb-3">My Records</h2>

<?php if (isset($_GET['success'])): ?>
  <div class="alert alert-success alert-dismissible fade show">
    Record saved successfully!
    <?php $r = get_record((int)$_GET['success']); if ($r && $r['output_filename']): ?>
      <a href="<?= h($r['output_filename']) ?>" target="_blank" class="btn btn-sm btn-success ms-2">View Document</a>
    <?php endif; ?>
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  </div>
<?php endif; ?>

<?php if (isset($_GET['deleted'])): ?>
  <div class="alert alert-info alert-dismissible fade show">
    Record deleted.
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  </div>
<?php endif; ?>

<?php if (isset($_GET['regenerated'])): ?>
  <div class="alert alert-success alert-dismissible fade show">
    Document regenerated.
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  </div>
<?php endif; ?>

<?php if (isset($_GET['regen_error'])): ?>
  <div class="alert alert-danger alert-dismissible fade show">
    Error regenerating: <?= h($_GET['regen_error']) ?>
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  </div>
<?php endif; ?>

  <!-- Search bar -->
  <form method="get" class="row g-2 mb-3">
    <div class="col-auto flex-grow-1">
      <input type="text" name="q" class="form-control" placeholder="Search records…"
             value="<?= h($search) ?>">
    </div>
    <div class="col-auto">
      <button type="submit" class="btn btn-outline-primary">Search</button>
      <?php if ($search): ?>
        <a href="records.php" class="btn btn-outline-secondary">Clear</a>
      <?php endif; ?>
    </div>
  </form>

  <?php if (empty($records)): ?>
    <div class="alert alert-secondary">
      No records found.
      <a href="questionnaire.php" class="btn btn-primary ms-2">Create your first record</a>
    </div>
  <?php else: ?>
  <div class="table-responsive">
    <table class="table table-hover align-middle">
      <thead class="table-light">
        <tr>
          <th>#</th>
          <th>Record Name</th>
          <th>Form</th>
          <th>Created</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <?php foreach ($records as $rec): ?>
        <tr>
          <td><?= (int)$rec['id'] ?></td>
          <td><?= h($rec['record_name']) ?></td>
          <td><span class="badge bg-secondary"><?= h($rec['form_number']) ?></span>
              <?= h($rec['form_title']) ?></td>
          <td><?= h(date('Y-m-d H:i', strtotime($rec['created_at']))) ?></td>
          <td class="text-nowrap">
            <?php if ($rec['output_filename'] && is_file(__DIR__ . '/' . $rec['output_filename'])): ?>
              <a href="<?= h($rec['output_filename']) ?>" target="_blank"
                 class="btn btn-sm btn-outline-primary" title="View">👁 View</a>
              <a href="<?= h($rec['output_filename']) ?>" download
                 class="btn btn-sm btn-outline-secondary" title="Download">⬇ Download</a>
            <?php else: ?>
              <a href="records.php?action=regenerate&id=<?= (int)$rec['id'] ?>"
                 class="btn btn-sm btn-outline-warning" title="Generate">⚙ Generate</a>
            <?php endif; ?>
            <a href="records.php?action=delete&id=<?= (int)$rec['id'] ?>"
               class="btn btn-sm btn-outline-danger"
               onclick="return confirm('Delete this record?')" title="Delete">🗑 Delete</a>
          </td>
        </tr>
        <?php endforeach; ?>
      </tbody>
    </table>
  </div>
  <?php endif; ?>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
