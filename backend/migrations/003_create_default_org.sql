-- Create default organization for testing
-- This org is used when no specific org is provided

-- Insert default organization if it doesn't exist
INSERT INTO organizations (id, name, plan, storage_used_gb, video_count)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'Default Organization',
    'free',
    0,
    0
)
ON CONFLICT (id) DO NOTHING;

-- Grant access to default org for testing
-- This allows events to be created without authentication
GRANT USAGE ON SCHEMA public TO anon;
GRANT ALL ON organizations TO anon;
GRANT ALL ON events TO anon;