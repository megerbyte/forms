-- Migration: Add Case Law and Citation Graph Tables
-- Date: 2025-10-02
-- Description: Creates tables for storing case law opinions, citation relationships,
--              unresolved citations, field-to-case links, and jurisdiction priorities.

-- Table: cases
-- Stores case law opinions from various sources (CourtListener, Texas courts, etc.)
CREATE TABLE IF NOT EXISTS cases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    case_name VARCHAR(500) NOT NULL,
    citation VARCHAR(255),
    court VARCHAR(255),
    jurisdiction VARCHAR(100),
    decision_date DATE,
    docket_number VARCHAR(255),
    full_text LONGTEXT,
    summary TEXT,
    url VARCHAR(500),
    source VARCHAR(100) DEFAULT 'courtlistener',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_citation (citation),
    INDEX idx_court (court),
    INDEX idx_jurisdiction (jurisdiction),
    INDEX idx_decision_date (decision_date),
    INDEX idx_source (source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: case_citations
-- Stores citation relationships between cases (case A cites case B)
CREATE TABLE IF NOT EXISTS case_citations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    citing_case_id INT NOT NULL,
    cited_case_id INT,
    citation_text VARCHAR(255) NOT NULL,
    context_text TEXT,
    treatment VARCHAR(50),
    page_number INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (citing_case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (cited_case_id) REFERENCES cases(id) ON DELETE SET NULL,
    INDEX idx_citing_case (citing_case_id),
    INDEX idx_cited_case (cited_case_id),
    INDEX idx_treatment (treatment)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: unresolved_citations
-- Stores citations that could not be resolved to a case in the database
CREATE TABLE IF NOT EXISTS unresolved_citations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    citing_case_id INT NOT NULL,
    citation_text VARCHAR(255) NOT NULL,
    context_text TEXT,
    reporter VARCHAR(100),
    volume INT,
    page INT,
    resolution_attempted_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (citing_case_id) REFERENCES cases(id) ON DELETE CASCADE,
    INDEX idx_citing_case (citing_case_id),
    INDEX idx_citation_text (citation_text),
    INDEX idx_reporter (reporter)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: field_case_links
-- Links canonical form fields to relevant case law
CREATE TABLE IF NOT EXISTS field_case_links (
    id INT AUTO_INCREMENT PRIMARY KEY,
    canonical_field_name VARCHAR(255) NOT NULL,
    case_id INT NOT NULL,
    relevance_score DECIMAL(3,2),
    notes TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    INDEX idx_canonical_field (canonical_field_name),
    INDEX idx_case (case_id),
    UNIQUE KEY unique_field_case (canonical_field_name, case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: jurisdiction_priority
-- Defines priority for jurisdictions when crawling/fetching cases
CREATE TABLE IF NOT EXISTS jurisdiction_priority (
    id INT AUTO_INCREMENT PRIMARY KEY,
    jurisdiction_name VARCHAR(100) NOT NULL UNIQUE,
    priority_level INT NOT NULL DEFAULT 50,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_priority (priority_level),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default jurisdiction priorities
INSERT INTO jurisdiction_priority (jurisdiction_name, priority_level, notes) VALUES
    ('Texas', 100, 'Highest priority - Texas state courts'),
    ('5th Circuit', 90, 'High priority - Federal 5th Circuit covering Texas'),
    ('Supreme Court', 85, 'High priority - U.S. Supreme Court'),
    ('1st Circuit', 50, 'Default priority - Federal circuits'),
    ('2nd Circuit', 50, 'Default priority - Federal circuits'),
    ('3rd Circuit', 50, 'Default priority - Federal circuits'),
    ('4th Circuit', 50, 'Default priority - Federal circuits'),
    ('6th Circuit', 50, 'Default priority - Federal circuits'),
    ('7th Circuit', 50, 'Default priority - Federal circuits'),
    ('8th Circuit', 50, 'Default priority - Federal circuits'),
    ('9th Circuit', 50, 'Default priority - Federal circuits'),
    ('10th Circuit', 50, 'Default priority - Federal circuits'),
    ('11th Circuit', 50, 'Default priority - Federal circuits'),
    ('DC Circuit', 50, 'Default priority - Federal D.C. Circuit'),
    ('Federal Circuit', 50, 'Default priority - Federal Circuit')
ON DUPLICATE KEY UPDATE priority_level=VALUES(priority_level);

-- Note: This migration assumes the following tables already exist from the main extraction system:
-- - form_fields (stores all extracted form fields)
-- - canonical_fields (stores canonical/deduplicated field names)
-- - field_synonyms (maps fields to canonical versions)
-- - field_options (stores option sets for fields)
-- - paragraph_groups (stores choose-one paragraph groups)
-- - form_field_values_wide (dynamic wide table for form data)
