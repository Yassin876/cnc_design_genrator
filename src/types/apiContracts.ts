/**
 * Section 37: Explicit API + Frontend Contract Types
 * Directly matched to Backend Pydantic Schemas
 */

export interface GeometryMetadata {
  vertices_count?: number;
  faces_count?: number;
  triangles_count?: number;
  is_watertight?: boolean;
  volume_mm3?: number;
  surface_area_mm2?: number;
  bounding_box?: {
    min: number[];
    max: number[];
    dimensions: { width: number; height: number; depth: number };
  };
}

export interface ModelAsset {
  id: string;
  project_id: string;
  version_id: string;
  format: 'STL' | 'STEP' | 'DXF' | 'OBJ' | 'IGES' | 'GLB';
  file_path: string;
  preview_path?: string;
  geometry_metadata: GeometryMetadata;
  dimensions: Record<string, any>;
  material: string;
  units: 'mm' | 'cm' | 'm' | 'inch';
  status: 'READY' | 'PROCESSING' | 'FAILED';
  created_at: string;
}

export interface ValidationIssue {
  id: string;
  category: 'Geometry' | 'Dimensions' | 'Mesh' | 'Manufacturing';
  problem: string;
  severity: 'PASS' | 'WARNING' | 'ERROR';
  location?: string;
  explanation: string;
  suggested_fix: string;
  fix_action?: string;
}

export interface ValidationResult {
  is_valid: boolean;
  is_watertight: boolean;
  bounding_box: {
    width: number;
    height: number;
    depth: number;
  };
  vertex_count: number;
  face_count: number;
  volume_mm3: number;
  surface_area_mm2: number;
  issues: ValidationIssue[];
  toolpath_clearance_passed: boolean;
}

export interface ProjectVersion {
  id: string;
  project_id: string;
  version_number: number;
  prompt: string;
  source_files: string[];
  generated_files: string[];
  model_metadata: GeometryMetadata;
  parameters: Record<string, any>;
  validation_result: Record<string, any>;
  created_at: string;
}

export interface Project {
  id: string;
  owner_id: string;
  name: string;
  description?: string;
  type: '2D' | '3D';
  current_version: number;
  status: 'ACTIVE' | 'ARCHIVED';
  created_at?: string;
  updated_at?: string;
  file_path?: string;
  metadata?: Record<string, any>;
}

export interface GenerationJob {
  id: string;
  project_id?: string;
  user_id?: string;
  job_type: 'text-to-3d' | 'image-to-3d' | 'text-to-2d' | 'image-to-2d' | 'ai-edit';
  design_type: '2D' | '3D';
  output_format: 'STL' | 'STEP' | 'DXF' | 'OBJ';
  status: 'queued' | 'processing' | 'understanding' | 'generating' | 'geometry_processing' | 'optimizing' | 'validating' | 'completed' | 'failed' | 'cancelled';
  stage_name?: string;
  progress?: number;
  text_prompt?: string;
  input_filename?: string;
  output_filename?: string;
  output_file_path?: string;
  created_at: string;
}

export interface ExportJob {
  id: string;
  input_file_path: string;
  export_format: 'STL' | 'STEP' | 'DXF' | 'OBJ' | 'IGES' | 'SVG' | 'GCODE';
  output_file_path?: string;
  output_filename?: string;
  status: 'PROCESSING' | 'COMPLETED' | 'FAILED';
  resolution?: 'coarse' | 'medium' | 'fine' | 'ultra';
  created_at: string;
}

export interface AIMessage {
  id: string;
  sender: 'user' | 'ai' | 'system';
  text: string;
  timestamp: string;
  attachments?: any[];
  explanation?: string;
  action?: {
    type: string;
    data: any;
  };
}
