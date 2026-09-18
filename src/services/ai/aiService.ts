import { apiClient, fetchWithRetry } from '../api/client';
import { JobProgressEvent } from '../../types';

export interface PromptUnderstandingResult {
  extractedParameters: Record<string, any>;
  designSpecification: string;
  recommendedMaterial: string;
  recommendedUnits: 'mm' | 'cm' | 'm' | 'inch';
  estimatedVolumeMm3: number;
}

export const aiService = {
  /**
   * Section 34: AI Generation Pipeline Service
   * Text Input → Prompt Understanding → Engineering Parameter Extraction → Design Spec → Geometry Generator → Mesh/CAD Processing → Validation → Preview → Workspace
   */
  understandPrompt: async (prompt: string): Promise<PromptUnderstandingResult> => {
    return fetchWithRetry(async () => {
      // Simulate backend prompt analysis / parameter extraction
      const wallMatch = prompt.match(/(?:wall thickness|thickness|wall)\s*(?:to|=)?\s*(\d+(?:\.\d+)?)\s*(mm|cm|inch)?/i);
      const diaMatch = prompt.match(/(?:inner diameter|diameter|id|od|radius)\s*(?:to|=)?\s*(\d+(?:\.\d+)?)\s*(mm|cm|inch)?/i);
      
      const extractedParameters: Record<string, any> = {
        wall_thickness: wallMatch ? parseFloat(wallMatch[1]) : 5,
        inner_diameter: diaMatch ? parseFloat(diaMatch[1]) : 50,
        bend_angle: prompt.toLowerCase().includes('45') ? 45 : 90,
      };

      return {
        extractedParameters,
        designSpecification: `Parametric CAD Specification for: "${prompt}"`,
        recommendedMaterial: prompt.toLowerCase().includes('aluminum') ? 'Aluminum 6061' : 'Industrial Steel 304',
        recommendedUnits: 'mm',
        estimatedVolumeMm3: 45200.0
      };
    });
  },

  generateTextTo3D: async (prompt: string, dimensions: any = { height: 100, width: 100, length: 100 }, userId?: string, projectId?: string) => {
    return fetchWithRetry(async () => {
      const dims = typeof dimensions === 'object' ? dimensions : { height: 100, width: 100, length: 100 };
      const res = await apiClient.post('/generation/text-to-3d', {
        user_id: userId,
        project_id: projectId,
        prompt,
        ...dims
      });
      return res.data;
    });
  },

  generateImageTo3D: async (imagePath: string, dimensions = { height: 100, width: 100, length: 100 }, userId?: string, projectId?: string) => {
    return fetchWithRetry(async () => {
      const res = await apiClient.post('/generation/image-to-3d', {
        user_id: userId,
        project_id: projectId,
        image_path: imagePath,
        ...dimensions
      });
      return res.data;
    });
  },

  generateTextTo2D: async (prompt: string, params = {}, userId?: string, projectId?: string) => {
    return fetchWithRetry(async () => {
      const res = await apiClient.post('/generation/text-to-2d', {
        user_id: userId,
        project_id: projectId,
        prompt,
        params
      });
      return res.data;
    });
  },

  generateImageTo2D: async (imagePath: string, prompt = "Vector Blueprint", params = {}, userId?: string, projectId?: string) => {
    return fetchWithRetry(async () => {
      const res = await apiClient.post('/generation/image-to-2d', {
        user_id: userId,
        project_id: projectId,
        image_path: imagePath,
        prompt,
        params
      });
      return res.data;
    });
  },

  /**
   * Section 35: AI Edit Pipeline Service
   * User prompt → Load Project → Load Current Model → Identify Parameter → Apply Modification → Regenerate Geometry → Validate → Create New Version → Return Updated Model
   */
  aiEdit: async (filePath: string, prompt: string, designType: '2D' | '3D' = '2D', userId?: string, projectId?: string) => {
    return fetchWithRetry(async () => {
      const res = await apiClient.post('/editing/ai', {
        user_id: userId,
        project_id: projectId,
        file_path: filePath,
        prompt,
        design_type: designType
      });
      return res.data;
    });
  },

  subscribeToJobProgress: (jobId: string, onEvent: (event: JobProgressEvent) => void, onError?: (err: any) => void) => {
    const eventSource = new EventSource(`http://127.0.0.1:8000/api/v1/generation/stream/${jobId}`);

    eventSource.onmessage = (e) => {
      try {
        const data: JobProgressEvent = JSON.parse(e.data);
        onEvent(data);
        if (['completed', 'failed', 'cancelled'].includes(data.status)) {
          eventSource.close();
        }
      } catch (err) {
        console.error('Error parsing SSE event', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE Connection error', err);
      if (onError) onError(err);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }
};
