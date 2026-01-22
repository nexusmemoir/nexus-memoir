-- NexusMemoir Database Migration
-- Version: 2.0 (Draft System)
-- Date: 2026-01-22

-- Add new columns to capsules table
ALTER TABLE capsules ADD COLUMN status TEXT DEFAULT 'draft';
ALTER TABLE capsules ADD COLUMN payment_status TEXT DEFAULT 'pending';
ALTER TABLE capsules ADD COLUMN published_at TEXT;

-- Update existing capsules to 'published' status
-- (Assuming all existing capsules were paid and published)
UPDATE capsules SET status = 'published' WHERE status IS NULL OR status = 'draft';
UPDATE capsules SET payment_status = 'completed' WHERE payment_status IS NULL OR payment_status = 'pending';
UPDATE capsules SET published_at = created_at WHERE published_at IS NULL;

-- Verify migration
SELECT 
    COUNT(*) as total_capsules,
    SUM(CASE WHEN status = 'draft' THEN 1 ELSE 0 END) as draft_count,
    SUM(CASE WHEN status = 'published' THEN 1 ELSE 0 END) as published_count,
    SUM(CASE WHEN payment_status = 'pending' THEN 1 ELSE 0 END) as pending_payments,
    SUM(CASE WHEN payment_status = 'completed' THEN 1 ELSE 0 END) as completed_payments
FROM capsules;

-- Optional: Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_capsules_status ON capsules(status);
CREATE INDEX IF NOT EXISTS idx_capsules_payment_status ON capsules(payment_status);
CREATE INDEX IF NOT EXISTS idx_capsules_published_at ON capsules(published_at);

-- Clean up orphaned draft capsules (older than 30 days)
-- Uncomment to enable:
-- DELETE FROM capsules 
-- WHERE status = 'draft' 
-- AND datetime(created_at) < datetime('now', '-30 days');
