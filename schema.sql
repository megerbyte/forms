-- Texas Civil Litigation Forms System
-- MySQL 5.7+ / MariaDB 10.2+ compatible schema
-- Run once: mysql -u <user> -p <dbname> < schema.sql

CREATE TABLE IF NOT EXISTS forms (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  form_number   VARCHAR(50)   NOT NULL,           -- e.g. "2B-1"
  title         VARCHAR(255)  NOT NULL,           -- e.g. "Petition - General Form"
  filename      VARCHAR(255)  NOT NULL UNIQUE,    -- e.g. "Form_2B-1_Petition_-_General_Form.html"
  created_at    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS form_sections (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  form_id         INT          NOT NULL,
  section_label   VARCHAR(10)  DEFAULT NULL,      -- e.g. "A"
  section_title   VARCHAR(255) DEFAULT NULL,      -- e.g. "Discovery Control Plan"
  display_order   INT          DEFAULT 0,
  FOREIGN KEY (form_id) REFERENCES forms(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS form_fields (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  form_id        INT          NOT NULL,
  section_id     INT          DEFAULT NULL,
  field_key      VARCHAR(255) NOT NULL,           -- snake_case key
  field_label    VARCHAR(500) NOT NULL,           -- human-readable label
  field_type     ENUM('text','textarea','date','choice','select') DEFAULT 'text',
  choices        TEXT         DEFAULT NULL,       -- JSON array for choice/select types
  is_required    TINYINT(1)   DEFAULT 0,
  display_order  INT          DEFAULT 0,
  FOREIGN KEY (form_id)    REFERENCES forms(id)         ON DELETE CASCADE,
  FOREIGN KEY (section_id) REFERENCES form_sections(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS form_records (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  form_id          INT          NOT NULL,
  record_name      VARCHAR(255) NOT NULL,         -- user-defined name
  output_filename  VARCHAR(255) DEFAULT NULL,     -- generated output file path
  created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  updated_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (form_id) REFERENCES forms(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS form_record_values (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  record_id   INT  NOT NULL,
  field_id    INT  NOT NULL,
  value       TEXT DEFAULT NULL,
  FOREIGN KEY (record_id) REFERENCES form_records(id) ON DELETE CASCADE,
  FOREIGN KEY (field_id)  REFERENCES form_fields(id)  ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
