"""
Admin Flask Application for Legal Forms System

Minimal Flask admin UI for managing extracted form fields, tooltips,
synonyms, and option lists. Provides basic CRUD operations.

WARNING: This is intentionally minimal and unauthenticated for internal
development use only. Production deployment requires:
- Authentication/authorization
- HTTPS/TLS
- CSRF protection
- Input validation
- Rate limiting

Author: Legal Forms Extraction System
Date: 2025-10-02
"""

import os
import logging
from datetime import datetime

from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

# Database
import mysql.connector
from mysql.connector import Error as MySQLError

# Environment variables
from dotenv import load_dotenv

load_dotenv()

# Configuration
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
FLASK_PORT = int(os.getenv('FLASK_PORT', '5000'))

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
app.config['DEBUG'] = FLASK_DEBUG


class DatabaseManager:
    """Database connection manager."""
    
    def __init__(self):
        self.config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '3306')),
            'user': os.getenv('DB_USER', 'forms_user'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'legal_forms'),
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci'
        }
    
    def get_connection(self):
        """Get database connection."""
        return mysql.connector.connect(**self.config)


db_manager = DatabaseManager()


# HTML Templates (inline for simplicity)
BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Legal Forms Admin - {{ title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            margin-bottom: 20px;
        }
        .header h1 {
            margin: 0;
        }
        .nav {
            background-color: #34495e;
            padding: 10px;
            margin-bottom: 20px;
        }
        .nav a {
            color: white;
            text-decoration: none;
            padding: 10px 15px;
            margin-right: 10px;
            display: inline-block;
        }
        .nav a:hover {
            background-color: #2c3e50;
        }
        .content {
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #3498db;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .btn {
            padding: 8px 16px;
            background-color: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 3px;
            border: none;
            cursor: pointer;
            display: inline-block;
        }
        .btn:hover {
            background-color: #2980b9;
        }
        .btn-danger {
            background-color: #e74c3c;
        }
        .btn-danger:hover {
            background-color: #c0392b;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"], textarea, select {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 3px;
            box-sizing: border-box;
        }
        textarea {
            min-height: 100px;
        }
        .flash {
            padding: 10px;
            margin-bottom: 20px;
            border-radius: 3px;
        }
        .flash-success {
            background-color: #2ecc71;
            color: white;
        }
        .flash-error {
            background-color: #e74c3c;
            color: white;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-number {
            font-size: 36px;
            font-weight: bold;
            color: #3498db;
        }
        .stat-label {
            color: #7f8c8d;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>Legal Forms Admin Panel</h1>
            <p style="margin: 5px 0 0 0; opacity: 0.8;">Field Management &amp; Configuration</p>
        </div>
    </div>
    
    <div class="nav">
        <div class="container">
            <a href="/">Home</a>
            <a href="/fields">Fields</a>
            <a href="/synonyms">Synonyms</a>
            <a href="/options">Options</a>
        </div>
    </div>
    
    <div class="container">
        {% for message in get_flashed_messages() %}
        <div class="flash flash-success">{{ message }}</div>
        {% endfor %}
        
        <div class="content">
            {% block content %}{% endblock %}
        </div>
    </div>
</body>
</html>
"""

INDEX_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
<h2>Dashboard</h2>

<div class="stats">
    <div class="stat-card">
        <div class="stat-number">{{ stats.total_fields }}</div>
        <div class="stat-label">Canonical Fields</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">{{ stats.total_synonyms }}</div>
        <div class="stat-label">Field Synonyms</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">{{ stats.total_options }}</div>
        <div class="stat-label">Field Options</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">{{ stats.total_cases }}</div>
        <div class="stat-label">Cases in Database</div>
    </div>
</div>

<h3>Quick Actions</h3>
<a href="/fields" class="btn">Manage Fields</a>
<a href="/synonyms" class="btn">View Synonyms</a>
<a href="/options" class="btn">Manage Options</a>

<h3>System Information</h3>
<p><strong>Database:</strong> {{ db_name }}</p>
<p><strong>Semantic Matching:</strong> {{ 'Enabled' if semantic_enabled else 'Disabled' }}</p>
{% endblock %}
"""

FIELDS_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
<h2>Canonical Fields</h2>

<table>
    <thead>
        <tr>
            <th>Field Name</th>
            <th>Data Type</th>
            <th>Tooltip</th>
            <th>Synonyms</th>
            <th>Options</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        {% for field in fields %}
        <tr>
            <td>{{ field.canonical_name }}</td>
            <td>{{ field.data_type }}</td>
            <td>{{ field.tooltip[:50] }}{% if field.tooltip|length > 50 %}...{% endif %}</td>
            <td>{{ field.synonym_count }}</td>
            <td>{{ field.option_count }}</td>
            <td>
                <a href="/fields/edit/{{ field.canonical_name }}" class="btn">Edit</a>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
"""

FIELD_EDIT_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
<h2>Edit Field: {{ field.canonical_name }}</h2>

<form method="POST">
    <div class="form-group">
        <label>Canonical Name:</label>
        <input type="text" name="canonical_name" value="{{ field.canonical_name }}" readonly>
    </div>
    
    <div class="form-group">
        <label>Data Type:</label>
        <select name="data_type">
            <option value="text" {% if field.data_type == 'text' %}selected{% endif %}>Text</option>
            <option value="date" {% if field.data_type == 'date' %}selected{% endif %}>Date</option>
            <option value="number" {% if field.data_type == 'number' %}selected{% endif %}>Number</option>
            <option value="email" {% if field.data_type == 'email' %}selected{% endif %}>Email</option>
            <option value="phone" {% if field.data_type == 'phone' %}selected{% endif %}>Phone</option>
            <option value="address" {% if field.data_type == 'address' %}selected{% endif %}>Address</option>
            <option value="currency" {% if field.data_type == 'currency' %}selected{% endif %}>Currency</option>
            <option value="boolean" {% if field.data_type == 'boolean' %}selected{% endif %}>Boolean</option>
        </select>
    </div>
    
    <div class="form-group">
        <label>Tooltip:</label>
        <textarea name="tooltip">{{ field.tooltip }}</textarea>
    </div>
    
    <button type="submit" class="btn">Save Changes</button>
    <a href="/fields" class="btn">Cancel</a>
</form>

<h3>Synonyms ({{ synonyms|length }})</h3>
<ul>
    {% for syn in synonyms %}
    <li>{{ syn.original_text }} <em>(from {{ syn.source_file }})</em></li>
    {% endfor %}
</ul>

<h3>Options ({{ options|length }})</h3>
<ul>
    {% for opt in options %}
    <li>{{ opt.option_value }}</li>
    {% endfor %}
</ul>
{% endblock %}
"""

SYNONYMS_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
<h2>Field Synonyms</h2>

<table>
    <thead>
        <tr>
            <th>Original Text</th>
            <th>Canonical Name</th>
            <th>Source File</th>
            <th>Created</th>
        </tr>
    </thead>
    <tbody>
        {% for syn in synonyms %}
        <tr>
            <td>{{ syn.original_text }}</td>
            <td><a href="/fields/edit/{{ syn.canonical_name }}">{{ syn.canonical_name }}</a></td>
            <td>{{ syn.source_file }}</td>
            <td>{{ syn.created_at }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
"""

OPTIONS_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
<h2>Field Options</h2>

<table>
    <thead>
        <tr>
            <th>Canonical Field</th>
            <th>Options</th>
        </tr>
    </thead>
    <tbody>
        {% for field, opts in options.items() %}
        <tr>
            <td><a href="/fields/edit/{{ field }}">{{ field }}</a></td>
            <td>
                {% for opt in opts %}
                <span style="background: #ecf0f1; padding: 3px 8px; margin: 2px; border-radius: 3px; display: inline-block;">
                    {{ opt.option_value }}
                </span>
                {% endfor %}
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
"""


# Routes
@app.route('/')
def index():
    """Dashboard page."""
    conn = db_manager.get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get statistics
    cursor.execute("SELECT COUNT(*) as count FROM canonical_fields")
    total_fields = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM field_synonyms")
    total_synonyms = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM field_options")
    total_options = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM cases")
    total_cases = cursor.fetchone()['count'] if cursor.rowcount > 0 else 0
    
    cursor.close()
    conn.close()
    
    stats = {
        'total_fields': total_fields,
        'total_synonyms': total_synonyms,
        'total_options': total_options,
        'total_cases': total_cases
    }
    
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', INDEX_TEMPLATE),
        title='Dashboard',
        stats=stats,
        db_name=os.getenv('DB_NAME', 'legal_forms'),
        semantic_enabled=os.getenv('ENABLE_SEMANTICS', 'false').lower() == 'true'
    )


@app.route('/fields')
def fields_list():
    """List all canonical fields."""
    conn = db_manager.get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get fields with counts
    cursor.execute("""
        SELECT 
            cf.canonical_name,
            cf.data_type,
            cf.tooltip,
            COUNT(DISTINCT fs.id) as synonym_count,
            COUNT(DISTINCT fo.id) as option_count
        FROM canonical_fields cf
        LEFT JOIN field_synonyms fs ON cf.canonical_name = fs.canonical_name
        LEFT JOIN field_options fo ON cf.canonical_name = fo.canonical_name
        GROUP BY cf.canonical_name, cf.data_type, cf.tooltip
        ORDER BY cf.canonical_name
    """)
    
    fields = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', FIELDS_TEMPLATE),
        title='Fields',
        fields=fields
    )


@app.route('/fields/edit/<field_name>', methods=['GET', 'POST'])
def field_edit(field_name):
    """Edit a field."""
    conn = db_manager.get_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        # Update field
        data_type = request.form.get('data_type')
        tooltip = request.form.get('tooltip')
        
        cursor.execute(
            "UPDATE canonical_fields SET data_type = %s, tooltip = %s WHERE canonical_name = %s",
            (data_type, tooltip, field_name)
        )
        conn.commit()
        
        flash(f'Field "{field_name}" updated successfully!')
        return redirect(url_for('fields_list'))
    
    # Get field
    cursor.execute("SELECT * FROM canonical_fields WHERE canonical_name = %s", (field_name,))
    field = cursor.fetchone()
    
    # Get synonyms
    cursor.execute("SELECT * FROM field_synonyms WHERE canonical_name = %s", (field_name,))
    synonyms = cursor.fetchall()
    
    # Get options
    cursor.execute("SELECT * FROM field_options WHERE canonical_name = %s ORDER BY display_order", (field_name,))
    options = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', FIELD_EDIT_TEMPLATE),
        title=f'Edit Field: {field_name}',
        field=field,
        synonyms=synonyms,
        options=options
    )


@app.route('/synonyms')
def synonyms_list():
    """List all synonyms."""
    conn = db_manager.get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT * FROM field_synonyms 
        ORDER BY canonical_name, original_text
    """)
    
    synonyms = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', SYNONYMS_TEMPLATE),
        title='Synonyms',
        synonyms=synonyms
    )


@app.route('/options')
def options_list():
    """List all field options."""
    conn = db_manager.get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT canonical_name, option_value, display_order
        FROM field_options
        ORDER BY canonical_name, display_order
    """)
    
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Group by field
    options = {}
    for row in results:
        field = row['canonical_name']
        if field not in options:
            options[field] = []
        options[field].append(row)
    
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', OPTIONS_TEMPLATE),
        title='Options',
        options=options
    )


# API endpoints
@app.route('/api/fields', methods=['GET'])
def api_fields():
    """API endpoint for fields list."""
    conn = db_manager.get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM canonical_fields")
    fields = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify(fields)


@app.route('/api/fields/<field_name>/options', methods=['GET'])
def api_field_options(field_name):
    """API endpoint for field options."""
    conn = db_manager.get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute(
        "SELECT * FROM field_options WHERE canonical_name = %s ORDER BY display_order",
        (field_name,)
    )
    options = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify(options)


def main():
    """Run the Flask app."""
    logger.info(f"Starting admin app on port {FLASK_PORT}")
    logger.warning("WARNING: This admin UI is unauthenticated and for internal dev use only!")
    app.run(host='0.0.0.0', port=FLASK_PORT, debug=FLASK_DEBUG)


if __name__ == '__main__':
    main()
