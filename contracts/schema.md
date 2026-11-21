# Database Schema Specification (SQLite with WAL & FTS5)

## Overview
- Engine: SQLite 3 with Write-Ahead Logging (`PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;`)
- Concurrency: Threaded connection pooling with SQLite WAL enabled.
- Location: `/app_data/db/apply.sqlite`
- Full-Text Search: SQLite FTS5 virtual table on jobs (`title`, `company`, `field`, `skills_text`, `location_text`).

## Entity Relationship Diagram
```mermaid
erDiagram
    inbox ||--o{ jobs : "originates"
    jobs ||--o{ job_sources : "merged from"
    jobs ||--o| drafts : "has draft"
    jobs ||--o| cv_artifacts : "has tailored cv"
    jobs ||--o| sends : "logs delivery"
    queue ||--o| inbox : "processes"
    settings ||--|| profile : "configures"
    llm_usage ||--o{ jobs : "tracks cost"
    noise_log ||--o| inbox : "records dropped"
    audit_log ||--o{ jobs : "tracks actions"

    inbox {
        string id PK
        string source_id
        string chat_id
        string chat_name
        string sender
        datetime timestamp
        text raw_text
        string media_path
        string media_mime
        string message_hash UK
        string status
        datetime created_at
    }

    jobs {
        string id PK
        string primary_inbox_id FK
        string title
        string company
        string field
        string location_text
        string work_mode
        string city
        float experience_min_years
        float experience_max_years
        string education
        json skills
        json responsibilities
        string deadline
        string shift_text
        boolean night_shift
        string gender_requirement
        string apply_method
        string apply_email
        string apply_whatsapp
        string apply_link
        string exact_subject
        boolean from_image
        json walkin_details
        boolean fresh_grad_ok
        string tier
        json tier_reasons
        float score
        string status
        text fit_summary
        json matches
        json gaps
        datetime created_at
        datetime updated_at
    }

    job_sources {
        string id PK
        string job_id FK
        string inbox_id FK
        string source_chat
        datetime detected_at
    }

    drafts {
        string id PK
        string job_id FK
        string recipient
        string subject
        text body
        boolean is_customized
        datetime created_at
        datetime updated_at
    }

    cv_artifacts {
        string id PK
        string job_id FK
        string pdf_path
        json preview_png_paths
        boolean passes_verifier
        text verifier_notes
        datetime generated_at
    }

    sends {
        string id PK
        string job_id FK
        string recipient
        string subject
        string gmail_message_id
        string status
        text error
        datetime sent_at
    }

    settings {
        string key PK
        text value
        datetime updated_at
    }

    profile {
        string id PK
        json data
        datetime updated_at
    }

    queue {
        string id PK
        string queue_name
        int priority
        json payload
        string status
        int retries
        datetime next_run_at
        text last_error
        datetime created_at
        datetime updated_at
    }

    llm_usage {
        string id PK
        string provider
        string model
        int input_tokens
        int output_tokens
        float cost_usd
        string post_hash
        datetime created_at
    }

    noise_log {
        string id PK
        string message_id
        string chat_id
        text preview
        string reason
        datetime created_at
    }

    audit_log {
        string id PK
        string entity_type
        string entity_id
        string action
        json details
        datetime created_at
    }
```

## Indexes
- `idx_jobs_tier_status`: `(tier, status, created_at DESC)`
- `idx_jobs_deadline`: `(deadline ASC)`
- `idx_jobs_company_title`: `(company, title)`
- `idx_inbox_hash`: `(message_hash)`
- `idx_queue_status_prio`: `(status, priority DESC, next_run_at ASC)`

## FTS5 Configuration
```sql
CREATE VIRTUAL TABLE jobs_fts USING fts5(
    job_id UNINDEXED,
    title,
    company,
    field,
    skills_text,
    location_text,
    content='jobs',
    content_rowid='rowid'
);
```
