-- Hockey Analytics Database Schema
-- Phase 1: Foundation Tables
-- This schema uses Supabase (PostgreSQL) with Row Level Security

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- ORGANIZATIONS TABLE (Multi-tenancy foundation)
-- ============================================
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    settings JSONB DEFAULT '{
        "video_quota_gb": 100,
        "max_users": 10,
        "features": {
            "ml_detection": true,
            "gemini_analysis": false,
            "training_export": false
        }
    }'::jsonb,
    
    CONSTRAINT slug_format CHECK (slug ~ '^[a-z0-9-]+$')
);

-- Create index for slug lookups
CREATE INDEX idx_organizations_slug ON organizations(slug);

-- ============================================
-- ORGANIZATION MEMBERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS organization_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'viewer',
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_role CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    UNIQUE(org_id, user_id)
);

CREATE INDEX idx_org_members_user ON organization_members(user_id);
CREATE INDEX idx_org_members_org ON organization_members(org_id);

-- ============================================
-- VIDEOS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- File information
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    file_size_bytes BIGINT,
    mime_type TEXT,
    
    -- Video metadata
    duration_seconds FLOAT,
    fps INTEGER,
    width INTEGER,
    height INTEGER,
    resolution TEXT GENERATED ALWAYS AS (width || 'x' || height) STORED,
    codec TEXT,
    bitrate INTEGER,
    
    -- Processing status
    status TEXT DEFAULT 'uploaded',
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,
    processing_error TEXT,
    
    -- Streaming
    hls_manifest_url TEXT,
    thumbnail_url TEXT,
    
    -- User tracking
    uploaded_by UUID REFERENCES auth.users(id),
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Game information
    game_date DATE,
    home_team TEXT,
    away_team TEXT,
    venue TEXT,
    game_type TEXT, -- 'regular', 'playoff', 'tournament', 'practice'
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    veo_metadata JSONB, -- VEO-specific metadata if available
    
    CONSTRAINT valid_status CHECK (status IN ('uploaded', 'processing', 'processed', 'failed', 'archived')),
    CONSTRAINT valid_game_type CHECK (game_type IS NULL OR game_type IN ('regular', 'playoff', 'tournament', 'practice', 'scrimmage'))
);

-- Indexes for performance
CREATE INDEX idx_videos_org ON videos(org_id);
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_uploaded_at ON videos(uploaded_at DESC);
CREATE INDEX idx_videos_game_date ON videos(game_date DESC);

-- ============================================
-- EVENTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    
    -- Event information
    event_type TEXT NOT NULL,
    timestamp_seconds FLOAT NOT NULL,
    end_timestamp_seconds FLOAT, -- For events with duration
    
    -- Detection information
    confidence_score FLOAT DEFAULT 0.0,
    detection_method TEXT, -- 'yolo', 'gemini', 'manual', 'imported'
    model_version TEXT,
    
    -- Verification
    verified BOOLEAN DEFAULT FALSE,
    verified_by UUID REFERENCES auth.users(id),
    verified_at TIMESTAMPTZ,
    verification_notes TEXT,
    
    -- Frame/location data
    frame_number INTEGER,
    bounding_boxes JSONB, -- Array of detected objects with coordinates
    frame_data JSONB, -- Additional ML detection data
    
    -- Event-specific data
    player_numbers INTEGER[], -- Jersey numbers involved
    team TEXT, -- 'home', 'away'
    period INTEGER,
    game_clock TEXT, -- MM:SS format
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_confidence CHECK (confidence_score >= 0 AND confidence_score <= 1),
    CONSTRAINT valid_event_type CHECK (event_type IN (
        'goal', 'shot', 'save', 'penalty', 'faceoff', 
        'offside', 'icing', 'hit', 'block', 'giveaway', 
        'takeaway', 'period_start', 'period_end', 
        'referee_signal', 'fight', 'timeout', 'injury'
    )),
    CONSTRAINT valid_team CHECK (team IS NULL OR team IN ('home', 'away')),
    CONSTRAINT valid_period CHECK (period IS NULL OR period BETWEEN 1 AND 10),
    CONSTRAINT valid_detection_method CHECK (detection_method IS NULL OR detection_method IN ('yolo', 'gemini', 'manual', 'imported'))
);

-- Indexes for performance
CREATE INDEX idx_events_video ON events(video_id, timestamp_seconds);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_org ON events(org_id);
CREATE INDEX idx_events_verified ON events(verified);
CREATE INDEX idx_events_timestamp ON events(video_id, timestamp_seconds);

-- ============================================
-- PROCESSING JOBS TABLE (Track async processing)
-- ============================================
CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    
    job_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    
    progress_percent INTEGER DEFAULT 0,
    current_step TEXT,
    error_message TEXT,
    
    worker_id TEXT,
    result JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_job_type CHECK (job_type IN ('hls_conversion', 'ml_detection', 'gemini_analysis', 'thumbnail_generation')),
    CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    CONSTRAINT valid_progress CHECK (progress_percent >= 0 AND progress_percent <= 100),
    CONSTRAINT valid_priority CHECK (priority BETWEEN 1 AND 10)
);

CREATE INDEX idx_jobs_status ON processing_jobs(status, priority DESC, created_at);
CREATE INDEX idx_jobs_video ON processing_jobs(video_id);

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_jobs ENABLE ROW LEVEL SECURITY;

-- Organizations: Users can only see orgs they belong to
CREATE POLICY "Users can view their organizations" ON organizations
    FOR SELECT USING (
        id IN (
            SELECT org_id FROM organization_members 
            WHERE user_id = auth.uid()
        )
    );

-- Organization Members: Users can see members of their orgs
CREATE POLICY "Users can view org members" ON organization_members
    FOR SELECT USING (
        org_id IN (
            SELECT org_id FROM organization_members 
            WHERE user_id = auth.uid()
        )
    );

-- Videos: Users can only access videos from their organizations
CREATE POLICY "Users can view their org's videos" ON videos
    FOR SELECT USING (
        org_id IN (
            SELECT org_id FROM organization_members 
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert videos to their org" ON videos
    FOR INSERT WITH CHECK (
        org_id IN (
            SELECT org_id FROM organization_members 
            WHERE user_id = auth.uid() 
            AND role IN ('owner', 'admin', 'member')
        )
    );

CREATE POLICY "Users can update their org's videos" ON videos
    FOR UPDATE USING (
        org_id IN (
            SELECT org_id FROM organization_members 
            WHERE user_id = auth.uid() 
            AND role IN ('owner', 'admin', 'member')
        )
    );

-- Events: Similar policies as videos
CREATE POLICY "Users can view their org's events" ON events
    FOR SELECT USING (
        org_id IN (
            SELECT org_id FROM organization_members 
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can manage their org's events" ON events
    FOR ALL USING (
        org_id IN (
            SELECT org_id FROM organization_members 
            WHERE user_id = auth.uid() 
            AND role IN ('owner', 'admin', 'member')
        )
    );

-- Processing Jobs: Users can see jobs for their org's videos
CREATE POLICY "Users can view their org's jobs" ON processing_jobs
    FOR SELECT USING (
        org_id IN (
            SELECT org_id FROM organization_members 
            WHERE user_id = auth.uid()
        )
    );

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to get user's organizations
CREATE OR REPLACE FUNCTION get_user_organizations(user_uuid UUID)
RETURNS TABLE(org_id UUID, org_name TEXT, user_role TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        o.id,
        o.name,
        om.role
    FROM organizations o
    INNER JOIN organization_members om ON o.id = om.org_id
    WHERE om.user_id = user_uuid;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if user has permission in org
CREATE OR REPLACE FUNCTION user_has_permission(user_uuid UUID, org_uuid UUID, required_role TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    user_role TEXT;
    role_hierarchy JSONB := '{
        "owner": 4,
        "admin": 3,
        "member": 2,
        "viewer": 1
    }'::jsonb;
BEGIN
    SELECT role INTO user_role
    FROM organization_members
    WHERE user_id = user_uuid AND org_id = org_uuid;
    
    IF user_role IS NULL THEN
        RETURN FALSE;
    END IF;
    
    RETURN (role_hierarchy->>user_role)::int >= (role_hierarchy->>required_role)::int;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- TRIGGERS
-- ============================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON processing_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================
-- SAMPLE DATA (for development)
-- ============================================
-- Uncomment to insert sample data

-- INSERT INTO organizations (name, slug) VALUES 
-- ('Demo Hockey Club', 'demo-hockey'),
-- ('Test Team', 'test-team');

-- Note: Remember to create corresponding auth.users entries in Supabase Auth
-- and link them via organization_members table