# Texas Civil Litigation Forms System

A web-based questionnaire system for filling out 80+ Texas civil litigation HTML forms
(from O'Connor's Texas Rules).  The system parses every HTML form, stores its structure
in a MySQL database, and walks users step-by-step through each form section to collect
the required information, then generates a completed HTML document.

---

## Requirements

| Requirement | Version |
|---|---|
| PHP | 7.4+ (8.x recommended) |
| MySQL / MariaDB | 5.7+ / 10.2+ |
| Web server | Apache / Nginx / `php -S` |

---

## Setup

### 1. Create the database

```bash
mysql -u root -p -e "CREATE DATABASE forms_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p forms_db < schema.sql
```

### 2. Configure the database connection

Edit `config/database.php` **or** set environment variables before starting PHP:

```bash
export DB_HOST=localhost
export DB_NAME=forms_db
export DB_USER=root
export DB_PASS=secret
```

### 3. Import forms into the database

**CLI:**
```bash
php import_forms.php
```

**Web:**  Navigate to `http://localhost/import_forms.php?confirm=1`

This scans all `*.html` files in the project root, extracts sections and placeholder
fields, and populates `forms`, `form_sections`, and `form_fields`.

### 4. Start a development server (optional)

```bash
php -S localhost:8080
```

Then open `http://localhost:8080/questionnaire.php` in your browser.

---

## Usage

### Questionnaire

1. Open `questionnaire.php`
2. **Step 0** – search for and select a form, then enter a record name (e.g. *Smith v. Jones*)
3. **Steps 1–N** – fill in the fields for each form section
4. **Review** – confirm your answers
5. **Save** – the system generates a filled HTML document in `output/`

### Records

Open `records.php` to view, download, or delete saved records.

---

## File Overview

| File | Purpose |
|---|---|
| `schema.sql` | MySQL schema (run once) |
| `config/database.php` | DB connection configuration |
| `import_forms.php` | Parse HTML forms → populate DB |
| `questionnaire.php` | Multi-step UI |
| `save_response.php` | Persist answers + trigger generation |
| `generate_form.php` | Fill placeholders → write output file |
| `records.php` | View / manage completed records |
| `includes/helpers.php` | Shared functions (db, sanitize, query helpers) |
| `output/` | Generated filled documents (git-ignored except `.gitkeep`) |

---

## Output Files

Generated documents are stored as `output/{record_id}_{record_name}.html`.
Unfilled placeholders are highlighted with a yellow dashed border so you can
see at a glance what still needs attention.