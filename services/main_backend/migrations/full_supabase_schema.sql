-- ==============================================================================
-- CAD Studio — Supabase PostgreSQL Database Schema Migration Script
-- Copy and paste this script directly into the Supabase SQL Editor to create all tables.
-- ==============================================================================

-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Users Table
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Projects Table
CREATE TABLE IF NOT EXISTS public.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    type VARCHAR(50) DEFAULT '3D',
    current_version INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    is_favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Project Versions Table
CREATE TABLE IF NOT EXISTS public.project_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    prompt TEXT,
    source_files JSONB DEFAULT '[]'::jsonb,
    generated_files JSONB DEFAULT '[]'::jsonb,
    model_metadata JSONB DEFAULT '{}'::jsonb,
    parameters JSONB DEFAULT '{}'::jsonb,
    validation_result JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. Models Table (CAD Model Artifacts)
CREATE TABLE IF NOT EXISTS public.models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE,
    version_id UUID REFERENCES public.project_versions(id) ON DELETE CASCADE,
    format VARCHAR(20) NOT NULL,
    file_path TEXT NOT NULL,
    preview_path TEXT,
    geometry_metadata JSONB DEFAULT '{}'::jsonb,
    dimensions JSONB DEFAULT '{}'::jsonb,
    material VARCHAR(100) DEFAULT 'Aluminum 6061',
    units VARCHAR(20) DEFAULT 'mm',
    status VARCHAR(50) DEFAULT 'READY',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. Input Files Table
CREATE TABLE IF NOT EXISTS public.input_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    original_name TEXT NOT NULL,
    file_type VARCHAR(50),
    mime_type VARCHAR(100),
    file_size_bytes BIGINT,
    storage_path TEXT NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 6. Output Files Table
CREATE TABLE IF NOT EXISTS public.output_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID,
    original_name TEXT NOT NULL,
    file_type VARCHAR(50),
    storage_path TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 7. Jobs Table (Job States & Tracking)
CREATE TABLE IF NOT EXISTS public.jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES public.projects(id) ON DELETE SET NULL,
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    job_type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'queued',
    stage_name VARCHAR(100) DEFAULT 'queued',
    progress INTEGER DEFAULT 0,
    design_type VARCHAR(20),
    output_format VARCHAR(20),
    text_prompt TEXT,
    input_file_id UUID REFERENCES public.input_files(id) ON DELETE SET NULL,
    output_file_id UUID REFERENCES public.output_files(id) ON DELETE SET NULL,
    processing_time_ms INTEGER,
    error JSONB NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE NULL
);

-- Foreign key link for output_files back to jobs table
ALTER TABLE public.output_files 
    ADD CONSTRAINT fk_output_files_jobs 
    FOREIGN KEY (job_id) REFERENCES public.jobs(id) ON DELETE SET NULL;

-- Indexes for optimal performance
CREATE INDEX IF NOT EXISTS idx_projects_owner ON public.projects(owner_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON public.projects(status);
CREATE INDEX IF NOT EXISTS idx_project_versions_proj ON public.project_versions(project_id);
CREATE INDEX IF NOT EXISTS idx_models_project ON public.models(project_id);
CREATE INDEX IF NOT EXISTS idx_jobs_user ON public.jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON public.jobs(status);
