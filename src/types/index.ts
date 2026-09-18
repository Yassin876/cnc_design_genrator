export * from './apiContracts';

export type ViewMode = 'auth' | 'home' | 'dashboard' | 'projects' | 'recent' | 'workspace_3d' | 'workspace_2d' | 'nesting' | 'templates' | 'favorites' | 'trash' | 'settings' | 'billing';

export interface PaymentMethodItem {
  id: string;
  user_id: string;
  provider: string;
  brand: string;
  last4: string;
  exp_month: number;
  exp_year: number;
  holder_name?: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export type JobStageState = 
  | 'queued'
  | 'processing'
  | 'understanding'
  | 'generating'
  | 'geometry_processing'
  | 'optimizing'
  | 'validating'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface User {
  id: string;
  name: string;
  email: string;
  token?: string;
  avatar_url?: string;
  created_at?: string;
  plan?: 'free' | 'pro' | 'pro_plus' | 'business' | string;
  requests_used_current_cycle?: number;
  cycle_start_date?: string;
  cycle_end_date?: string;
  is_admin?: boolean;
}

export type PlanId = 'free' | 'pro' | 'pro_plus' | 'business';

export interface PlanDetails {
  id: PlanId;
  name: string;
  price: number;
  price_currency: string;
  requests_limit: number;
  description: string;
  features: string[];
}

export interface SubscriptionStatus {
  user_id: string;
  plan: PlanId;
  plan_display_name: string;
  requests_used: number;
  requests_limit: number;
  requests_remaining: number;
  cycle_start_date: string | null;
  cycle_end_date: string | null;
  is_admin: boolean;
  plans_catalog: Record<string, PlanDetails>;
  paddle_customer_id?: string | null;
  paddle_subscription_id?: string | null;
  subscription_status?: string | null;
  next_billing_date?: string | null;
  cancel_url?: string | null;
  update_url?: string | null;
}

export interface PaymentRecord {
  id: string;
  user_id?: string;
  user_name?: string;
  user_email?: string;
  plan_requested: string;
  amount: number;
  currency: string;
  method: 'cash' | 'instapay' | string;
  proof_reference?: string;
  proof_image_path?: string;
  status: 'pending_approval' | 'approved' | 'rejected' | string;
  created_at: string;
  reviewed_at?: string;
  reviewed_by?: string;
  admin_notes?: string;
}

export interface PaymentConfig {
  instapay: {
    enabled: boolean;
    account_name: string;
    account_handle_or_number: string;
    phone_number: string;
    instructions: string;
    is_placeholder: boolean;
  };
  cash: {
    enabled: boolean;
    contact_person: string;
    contact_phone: string;
    office_address: string;
    instructions: string;
    is_placeholder: boolean;
  };
}


export interface Project {
  id: string;
  owner_id: string;
  name: string;
  description?: string;
  type: string;
  current_version: number;
  status: string;
  created_at?: string;
  updated_at?: string;
  file_path?: string;
  metadata?: Record<string, any>;
}

export interface ProjectVersion {
  id: string;
  project_id: string;
  version_number: number;
  prompt: string;
  source_files: string[];
  generated_files: string[];
  model_metadata: Record<string, any>;
  parameters: Record<string, any>;
  validation_result: Record<string, any>;
  created_at: string;
}

export interface Model {
  id: string;
  project_id: string;
  version_id: string;
  format: string;
  file_path: string;
  preview_path?: string;
  geometry_metadata: Record<string, any>;
  dimensions: Record<string, any>;
  material: string;
  units: string;
  status: string;
  created_at: string;
}

export interface TreeNode {
  id: string;
  name: string;
  type: 'Project' | 'Assembly' | 'Body' | 'Component' | 'Hole' | 'Fillet' | 'Flange' | 'Surface';
  visible: boolean;
  expanded?: boolean;
  selected?: boolean;
  children?: TreeNode[];
  parentId?: string | null;
  properties?: {
    dimensions?: Record<string, number>;
    material?: string;
    color?: string;
    features?: string[];
  };
}

export interface ModelTransform {
  position: { x: number; y: number; z: number };
  rotation: { x: number; y: number; z: number };
  scale: { x: number; y: number; z: number };
}

export interface FileAttachment {
  id: string;
  filename: string;
  file_path: string;
  file_size: number;
  format: string;
  extracted_metadata?: Record<string, any>;
  upload_timestamp: string;
}

export interface JobProgressEvent {
  job_id: string;
  status: JobStageState;
  stage_name: string;
  progress: number;
  message: string;
  output_file_path?: string;
  output_filename?: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  project_id: string;
  design_type: '2D' | '3D';
  title: string;
  active_file_path?: string | null;
  is_pinned?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ChatMessage {
  id: string;
  conversation_id?: string;
  sender: 'user' | 'ai' | 'system';
  text: string;
  timestamp: string;
  attachments?: FileAttachment[];
  explanation?: string;
  action?: {
    type: string;
    data: any;
  };
}


export interface GenerationHistoryItem {
  id: string;
  prompt: string;
  workflow: '3d' | '2d';
  timestamp: string;
  status: 'completed' | 'failed' | 'processing';
  model_url?: string;
  dxf_url?: string;
}


// Global Electron API Type Definition
declare global {
  interface Window {
    electronAPI?: {
      openFileDialog: (options?: Record<string, unknown>) => Promise<string | null>;
      saveFileDialog: (defaultName?: string) => Promise<string | null>;
      getBackendStatus?: () => Promise<Record<string, unknown>>;
      googleLogin?: () => Promise<{ code?: string; redirect_uri?: string; error?: string }>;
    };
  }
}

export interface GenerationJob {
  id: string;
  job_type: string;
  design_type: '2D' | '3D';
  output_format: string;
  status: JobStageState;
  stage_name?: string;
  progress?: number;
  text_prompt?: string;
  created_at: string;
  input_filename?: string;
  output_filename?: string;
  output_file_path?: string;
}

export interface BoundingBox {
  width: number;
  height: number;
  depth: number;
  min?: number[];
  max?: number[];
}

export interface MeshInspection {
  file_name: string;
  vertices_count: number;
  faces_count: number;
  triangles_count?: number;
  is_watertight: boolean;
  volume_mm3: number;
  surface_area_mm2: number;
  mesh_quality?: {
    aspect_ratio_ok: boolean;
    duplicate_vertices: number;
    degenerate_faces: number;
    non_manifold_edges: number;
  };
  bounding_box: {
    min: number[];
    max: number[];
    dimensions: BoundingBox;
    center: number[];
  };
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

export interface ValidationReport {
  is_valid: boolean;
  is_watertight: boolean;
  bounding_box: BoundingBox;
  vertex_count: number;
  face_count: number;
  volume_mm3: number;
  surface_area_mm2: number;
  issues: ValidationIssue[];
  toolpath_clearance_passed: boolean;
}

export interface NestResult {
  output_dir: string;
  total_parts_required: number;
  total_parts_placed: number;
  total_parts_unplaced: number;
  total_sheets_used: number;
  total_utilization: number;
  total_waste: number;
  sheets: Array<{
    sheet_index: number;
    sheet_name: string;
    parts_count: number;
    utilization: number;
    dxf_path: string;
  }>;
}




export interface CNCProjectBundle {
  metadata: {
    title: string;
    created_at: string;
    updated_at: string;
    version: string;
    author: string;
    units: 'mm' | 'in';
    material: string;
  };
  parameters: Record<string, any>;
  versions: ProjectVersion[];
  tree: TreeNode[];
  chat_history: ChatMessage[];
  validation_results?: ValidationReport;
  assets: {
    models: string[];
    drawings: string[];
    attachments: string[];
  };
}

