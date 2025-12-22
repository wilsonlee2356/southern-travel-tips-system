-- Migration script to add n8n_status column to auto_search_config table
-- Run this script directly on your database if Alembic migration doesn't work

-- For SQLite:
ALTER TABLE auto_search_config ADD COLUMN n8n_status TEXT NOT NULL DEFAULT 'pending';

-- For PostgreSQL (if using):
-- ALTER TABLE auto_search_config ADD COLUMN n8n_status VARCHAR NOT NULL DEFAULT 'pending';

-- Update existing rows to have 'pending' status (should already be default, but just in case)
UPDATE auto_search_config SET n8n_status = 'pending' WHERE n8n_status IS NULL;

