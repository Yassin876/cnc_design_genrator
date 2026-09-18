import { apiClient } from './client';
import { useAuthStore } from '../../app/store/useAuthStore';

export interface TextTo3DRequest {
  user_id: string;
  project_id?: string;
  prompt: string;
  height?: number;
  width?: number;
  length?: number;
}

export interface ImageTo3DRequest {
  user_id: string;
  project_id?: string;
  image_path: string;
  height?: number;
  width?: number;
  length?: number;
}

export interface Edit3DRequest {
  user_id: string;
  project_id?: string;
  file_path: string;  // Existing STL/GLB file to edit
  prompt: string;     // Edit instruction
  height?: number;
  width?: number;
  length?: number;
}

export interface TextTo2DRequest {
  user_id: string;
  project_id?: string;
  prompt: string;
  params?: Record<string, any>;
}

export interface ImageTo2DRequest {
  user_id: string;
  project_id?: string;
  image_path: string;
  prompt?: string;
  params?: Record<string, any>;
}

export interface JobResponse {
  job_id: string;
  status: string;
  message: string;
  output_file_path?: string;
  output_filename?: string;
  dxf_content?: string;   // For 2D external API responses
  dxf_url?: string;       // For 2D external API responses
}

export interface JobProgressEvent {
  job_id: string;
  status: string;
  stage_name: string;
  progress: number;
  message: string;
  output_file_path?: string;
  output_filename?: string;
  dxf_content?: string;   // For 2D external API responses
  dxf_url?: string;       // For 2D external API responses
}

/**
 * Normalise a raw backend response into a JobResponse.
 * The backend may return {job_id, status} or {status:"completed", output_file_path} directly.
 * For 2D external API, it may return {dxf_content} or {dxf_url} instead of file paths.
 */
function normalizeJobResponse(data: any): JobResponse {
  return {
    job_id: data.job_id || `local_${Date.now()}`,
    status: data.status || 'completed',
    message: data.message || '',
    output_file_path: data.output_file_path,
    output_filename: data.output_filename,
    dxf_content: data.dxf_content,
    dxf_url: data.dxf_url,
  };
}

export const generationApiService = {
  textTo3D: async (req: TextTo3DRequest): Promise<JobResponse> => {
    const res = await apiClient.post('/generation/text-to-3d', req);
    return normalizeJobResponse(res.data);
  },

  imageTo3D: async (req: ImageTo3DRequest): Promise<JobResponse> => {
    const res = await apiClient.post('/generation/image-to-3d', req);
    const response = normalizeJobResponse(res.data);

    // If the job is processing, we need to track it via streaming
    if (response.status === 'processing' && response.job_id) {
      console.log(`[generationApi] imageTo3D started as background job: ${response.job_id}`);
      // The caller should use streamJobProgress to track this job
    }

    return response;
  },

  edit3D: async (req: Edit3DRequest): Promise<JobResponse> => {
    const res = await apiClient.post('/generation/edit-3d', req);
    const response = normalizeJobResponse(res.data);

    // If the job is processing, we need to track it via streaming
    if (response.status === 'processing' && response.job_id) {
      console.log(`[generationApi] edit3D started as background job: ${response.job_id}`);
      // The caller should use streamJobProgress to track this job
    }

    return response;
  },

  textTo2D: async (req: TextTo2DRequest): Promise<JobResponse> => {
    const res = await apiClient.post('/generation/text-to-2d', req);
    return normalizeJobResponse(res.data);
  },

  imageTo2D: async (req: ImageTo2DRequest): Promise<JobResponse> => {
    const res = await apiClient.post('/generation/image-to-2d', req);
    return normalizeJobResponse(res.data);
  },

  getJob: async (jobId: string): Promise<any> => {
    const res = await apiClient.get(`/generation/jobs/${jobId}`);
    return res.data;
  },

  streamJobProgress: (jobId: string): EventSource => {
    // EventSource doesn't support custom headers, so we pass the token as a query parameter
    const token = useAuthStore.getState().user?.token;
    const url = token 
      ? `${apiClient.defaults.baseURL}/generation/stream/${jobId}?token=${encodeURIComponent(token)}`
      : `${apiClient.defaults.baseURL}/generation/stream/${jobId}`;
    return new EventSource(url);
  }
};

