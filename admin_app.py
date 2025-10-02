#!/usr/bin/env python3
"""
Legal Forms Admin UI

Flask-based admin interface for managing field metadata, editing tooltips,
and viewing extracted fields.

Author: Legal Forms Extraction System
License: MIT
"""

import os
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'legal_forms'),
}


def get_db():
    """Get database connection."""
    return mysql.connector.connect(**DB_CONFIG)


# HTML Templates (embedded for simplicity)
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Legal Forms Admin{% endblock %}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background: #2c3e50;
            color: white;
            padding: 20px 0;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        header h1 {
            font-size: 24px;
            font-weight: 600;
        }
        nav {
            margin-top: 15px;
        }
        nav a {
            color: white;
            text-decoration: none;
            margin-right: 20px;
            padding: 8px 15px;
            border-radius: 4px;
            transition: background 0.3s;
        }
        nav a:hover {
            background: rgba(255,255,255,0.1);
        }
        nav a.active {
            background: rgba(255,255,255,0.2);
        }
        .card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .card h2 {
            font-size: 20px;
            margin-bottom: 15px;
            color: #2c3e50;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .btn {
            display: inline-block;
            padding: 8px 16px;
            background: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            border: none;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }
        .btn:hover {
            background: #2980b9;
        }
        .btn-small {
            padding: 4px 8px;
            font-size: 12px;
        }
        .btn-secondary {
            background: #95a5a6;
        }
        .btn-secondary:hover {
            background: #7f8c8d;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #2c3e50;
        }
        .form-group input,
        .form-group textarea,
        .form-group select {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            font-family: inherit;
        }
        .form-group textarea {
            resize: vertical;
            min-height: 100px;
        }
        .alert {
            padding: 12px 20px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .alert-success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .alert-error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            font-size: 12px;
            border-radius: 3px;
            background: #e9ecef;
            color: #495057;
        }
        .badge-primary {
            background: #3498db;
            color: white;
        }
        .search-box {
            margin-bottom: 20px;
        }
        .search-box input {
            width: 100%;
            padding: 10px 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-card .number {
            font-size: 32px;
            font-weight: 700;
            color: #3498db;
            margin-bottom: 5px;
        }
        .stat-card .label {
            font-size: 14px;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        code {
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>⚖️ Legal Forms Admin</h1>
            <nav>
                <a href="{{ url_for('index') }}" {% if request.endpoint == 'index' %}class="active"{% endif %}>Dashboard</a>
                <a href="{{ url_for('fields') }}" {% if request.endpoint == 'fields' %}class="active"{% endif %}>Fields</a>
                <a href="{{ url_for('forms') }}" {% if request.endpoint == 'forms' %}class="active"{% endif %}>Forms</a>
            </nav>
        </div>
    </header>
    
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

INDEX_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Dashboard - Legal Forms Admin{% endblock %}
{% block content %}
<h1 style="margin-bottom: 20px;">Dashboard</h1>

<div class="stats">
    <div class="stat-card">
        <div class="number">{{ stats.total_forms }}</div>
        <div class="label">Forms</div>
    </div>
    <div class="stat-card">
        <div class="number">{{ stats.total_fields }}</div>
        <div class="label">Unique Fields</div>
    </div>
    <div class="stat-card">
        <div class="number">{{ stats.total_synonyms }}</div>
        <div class="label">Field Synonyms</div>
    </div>
    <div class="stat-card">
        <div class="number">{{ stats.total_options }}</div>
        <div class="label">Field Options</div>
    </div>
</div>

<div class="card">
    <h2>Recent Forms</h2>
    {% if recent_forms %}
    <table>
        <thead>
            <tr>
                <th>Filename</th>
                <th>Type</th>
                <th>Fields</th>
                <th>Last Updated</th>
            </tr>
        </thead>
        <tbody>
            {% for form in recent_forms %}
            <tr>
                <td><a href="{{ url_for('view_form', form_id=form.id) }}">{{ form.filename }}</a></td>
                <td><span class="badge">{{ form.file_type }}</span></td>
                <td>{{ form.field_count }}</td>
                <td>{{ form.last_updated }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p>No forms found. Run the extraction script first.</p>
    {% endif %}
</div>

<div class="card">
    <h2>Quick Start</h2>
    <ol style="margin-left: 20px;">
        <li>Run extraction: <code>python legal_forms_extractor.py</code></li>
        <li>Browse extracted fields in the <a href="{{ url_for('fields') }}">Fields</a> section</li>
        <li>Edit field tooltips and metadata</li>
        <li>View forms and their fields in the <a href="{{ url_for('forms') }}">Forms</a> section</li>
    </ol>
</div>
{% endblock %}
"""

FIELDS_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Fields - Legal Forms Admin{% endblock %}
{% block content %}
<h1 style="margin-bottom: 20px;">Field Metadata</h1>

<div class="search-box">
    <input type="text" id="searchInput" placeholder="Search fields by name..." onkeyup="filterTable()">
</div>

<div class="card">
    {% if fields %}
    <table id="fieldsTable">
        <thead>
            <tr>
                <th>Canonical Name</th>
                <th>Display Name</th>
                <th>Data Type</th>
                <th>Tooltip</th>
                <th>Synonyms</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for field in fields %}
            <tr>
                <td><code>{{ field.canonical_name }}</code></td>
                <td>{{ field.display_name }}</td>
                <td><span class="badge">{{ field.data_type }}</span></td>
                <td>{{ field.tooltip[:100] }}{% if field.tooltip|length > 100 %}...{% endif %}</td>
                <td><span class="badge badge-primary">{{ field.synonym_count }}</span></td>
                <td>
                    <a href="{{ url_for('edit_field', field_id=field.id) }}" class="btn btn-small">Edit</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p>No fields found. Run the extraction script first.</p>
    {% endif %}
</div>

<script>
function filterTable() {
    const input = document.getElementById('searchInput');
    const filter = input.value.toUpperCase();
    const table = document.getElementById('fieldsTable');
    const tr = table.getElementsByTagName('tr');
    
    for (let i = 1; i < tr.length; i++) {
        const td = tr[i].getElementsByTagName('td');
        let found = false;
        
        for (let j = 0; j < td.length - 1; j++) {
            if (td[j]) {
                const txtValue = td[j].textContent || td[j].innerText;
                if (txtValue.toUpperCase().indexOf(filter) > -1) {
                    found = true;
                    break;
                }
            }
        }
        
        tr[i].style.display = found ? '' : 'none';
    }
}
</script>
{% endblock %}
"""

EDIT_FIELD_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Edit Field - Legal Forms Admin{% endblock %}
{% block content %}
<h1 style="margin-bottom: 20px;">Edit Field</h1>

<div class="card">
    <form method="POST">
        <div class="form-group">
            <label>Canonical Name (read-only)</label>
            <input type="text" value="{{ field.canonical_name }}" disabled>
        </div>
        
        <div class="form-group">
            <label for="display_name">Display Name</label>
            <input type="text" id="display_name" name="display_name" value="{{ field.display_name }}" required>
        </div>
        
        <div class="form-group">
            <label for="data_type">Data Type</label>
            <select id="data_type" name="data_type">
                <option value="text" {% if field.data_type == 'text' %}selected{% endif %}>Text</option>
                <option value="date" {% if field.data_type == 'date' %}selected{% endif %}>Date</option>
                <option value="integer" {% if field.data_type == 'integer' %}selected{% endif %}>Integer</option>
                <option value="decimal" {% if field.data_type == 'decimal' %}selected{% endif %}>Decimal</option>
                <option value="currency" {% if field.data_type == 'currency' %}selected{% endif %}>Currency</option>
                <option value="email" {% if field.data_type == 'email' %}selected{% endif %}>Email</option>
                <option value="phone" {% if field.data_type == 'phone' %}selected{% endif %}>Phone</option>
                <option value="boolean" {% if field.data_type == 'boolean' %}selected{% endif %}>Boolean</option>
            </select>
        </div>
        
        <div class="form-group">
            <label for="tooltip">Tooltip / Help Text</label>
            <textarea id="tooltip" name="tooltip">{{ field.tooltip }}</textarea>
        </div>
        
        <button type="submit" class="btn">Save Changes</button>
        <a href="{{ url_for('fields') }}" class="btn btn-secondary">Cancel</a>
    </form>
</div>

<div class="card">
    <h2>Synonyms</h2>
    {% if synonyms %}
    <table>
        <thead>
            <tr>
                <th>Raw Text</th>
                <th>Source Form</th>
            </tr>
        </thead>
        <tbody>
            {% for syn in synonyms %}
            <tr>
                <td>{{ syn.raw_text }}</td>
                <td>{% if syn.filename %}<a href="{{ url_for('view_form', form_id=syn.source_form_id) }}">{{ syn.filename }}</a>{% else %}N/A{% endif %}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p>No synonyms found.</p>
    {% endif %}
</div>
{% endblock %}
"""

FORMS_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Forms - Legal Forms Admin{% endblock %}
{% block content %}
<h1 style="margin-bottom: 20px;">Forms</h1>

<div class="card">
    {% if forms %}
    <table>
        <thead>
            <tr>
                <th>Filename</th>
                <th>Type</th>
                <th>Fields</th>
                <th>Last Updated</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for form in forms %}
            <tr>
                <td>{{ form.filename }}</td>
                <td><span class="badge">{{ form.file_type }}</span></td>
                <td>{{ form.field_count }}</td>
                <td>{{ form.last_updated }}</td>
                <td>
                    <a href="{{ url_for('view_form', form_id=form.id) }}" class="btn btn-small">View</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p>No forms found. Run the extraction script first.</p>
    {% endif %}
</div>
{% endblock %}
"""

VIEW_FORM_TEMPLATE = """
{% extends "base.html" %}
{% block title %}{{ form.filename }} - Legal Forms Admin{% endblock %}
{% block content %}
<h1 style="margin-bottom: 20px;">{{ form.filename }}</h1>

<div class="card">
    <h2>Form Information</h2>
    <table style="width: auto;">
        <tr><th>Filename:</th><td>{{ form.filename }}</td></tr>
        <tr><th>Type:</th><td><span class="badge">{{ form.file_type }}</span></td></tr>
        <tr><th>Path:</th><td><code>{{ form.file_path }}</code></td></tr>
        <tr><th>Extracted:</th><td>{{ form.extraction_date }}</td></tr>
        <tr><th>Last Updated:</th><td>{{ form.last_updated }}</td></tr>
    </table>
</div>

<div class="card">
    <h2>Fields ({{ fields|length }})</h2>
    {% if fields %}
    <table>
        <thead>
            <tr>
                <th>Canonical Name</th>
                <th>Display Name</th>
                <th>Data Type</th>
                <th>Occurrences</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for field in fields %}
            <tr>
                <td><code>{{ field.canonical_name }}</code></td>
                <td>{{ field.display_name }}</td>
                <td><span class="badge">{{ field.data_type }}</span></td>
                <td><span class="badge badge-primary">{{ field.occurrence_count }}</span></td>
                <td>
                    <a href="{{ url_for('edit_field', field_id=field.field_id) }}" class="btn btn-small">Edit</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p>No fields found for this form.</p>
    {% endif %}
</div>

<a href="{{ url_for('forms') }}" class="btn btn-secondary">Back to Forms</a>
{% endblock %}
"""


@app.route('/')
def index():
    """Dashboard."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Get statistics
    cursor.execute("SELECT COUNT(*) as cnt FROM forms")
    total_forms = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT COUNT(*) as cnt FROM fields")
    total_fields = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT COUNT(*) as cnt FROM synonyms")
    total_synonyms = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT COUNT(*) as cnt FROM field_options")
    total_options = cursor.fetchone()['cnt']
    
    stats = {
        'total_forms': total_forms,
        'total_fields': total_fields,
        'total_synonyms': total_synonyms,
        'total_options': total_options,
    }
    
    # Get recent forms
    cursor.execute("""
        SELECT f.*, COUNT(ff.field_id) as field_count
        FROM forms f
        LEFT JOIN form_fields ff ON f.id = ff.form_id
        GROUP BY f.id
        ORDER BY f.last_updated DESC
        LIMIT 10
    """)
    recent_forms = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    return render_template_string(BASE_TEMPLATE + INDEX_TEMPLATE, stats=stats, recent_forms=recent_forms)


@app.route('/fields')
def fields():
    """List all fields."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT f.*, COUNT(s.id) as synonym_count
        FROM fields f
        LEFT JOIN synonyms s ON f.id = s.field_id
        GROUP BY f.id
        ORDER BY f.canonical_name
    """)
    fields_list = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    return render_template_string(BASE_TEMPLATE + FIELDS_TEMPLATE, fields=fields_list)


@app.route('/fields/<int:field_id>/edit', methods=['GET', 'POST'])
def edit_field(field_id):
    """Edit a field."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    if request.method == 'POST':
        # Update field
        display_name = request.form.get('display_name')
        data_type = request.form.get('data_type')
        tooltip = request.form.get('tooltip')
        
        cursor.execute("""
            UPDATE fields
            SET display_name = %s, data_type = %s, tooltip = %s
            WHERE id = %s
        """, (display_name, data_type, tooltip, field_id))
        db.commit()
        
        flash('Field updated successfully!', 'success')
        return redirect(url_for('fields'))
    
    # Get field
    cursor.execute("SELECT * FROM fields WHERE id = %s", (field_id,))
    field = cursor.fetchone()
    
    if not field:
        flash('Field not found', 'error')
        return redirect(url_for('fields'))
    
    # Get synonyms
    cursor.execute("""
        SELECT s.*, f.filename
        FROM synonyms s
        LEFT JOIN forms f ON s.source_form_id = f.id
        WHERE s.field_id = %s
        ORDER BY s.raw_text
    """, (field_id,))
    synonyms = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    return render_template_string(BASE_TEMPLATE + EDIT_FIELD_TEMPLATE, field=field, synonyms=synonyms)


@app.route('/forms')
def forms():
    """List all forms."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT f.*, COUNT(ff.field_id) as field_count
        FROM forms f
        LEFT JOIN form_fields ff ON f.id = ff.form_id
        GROUP BY f.id
        ORDER BY f.filename
    """)
    forms_list = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    return render_template_string(BASE_TEMPLATE + FORMS_TEMPLATE, forms=forms_list)


@app.route('/forms/<int:form_id>')
def view_form(form_id):
    """View a form."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Get form
    cursor.execute("SELECT * FROM forms WHERE id = %s", (form_id,))
    form = cursor.fetchone()
    
    if not form:
        flash('Form not found', 'error')
        return redirect(url_for('forms'))
    
    # Get fields
    cursor.execute("""
        SELECT ff.*, f.canonical_name, f.display_name, f.data_type
        FROM form_fields ff
        JOIN fields f ON ff.field_id = f.id
        WHERE ff.form_id = %s
        ORDER BY f.canonical_name
    """, (form_id,))
    fields = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    return render_template_string(BASE_TEMPLATE + VIEW_FORM_TEMPLATE, form=form, fields=fields)


if __name__ == '__main__':
    print("=" * 60)
    print("Legal Forms Admin UI")
    print("=" * 60)
    print("\nStarting Flask development server...")
    print("Visit: http://localhost:5000")
    print("\nPress Ctrl+C to stop")
    print("=" * 60)
    
    app.run(debug=True, port=5000)
