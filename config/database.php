<?php
// -------------------------------------------------------
// Database configuration
// Adjust these values for your environment or use a
// .env-style override by setting environment variables
// before this file is included.
// -------------------------------------------------------

define('DB_HOST',     getenv('DB_HOST')     ?: 'localhost');
define('DB_NAME',     getenv('DB_NAME')     ?: 'forms_db');
define('DB_USER',     getenv('DB_USER')     ?: 'root');
define('DB_PASS',     getenv('DB_PASS')     ?: '');
define('DB_CHARSET',  'utf8mb4');
