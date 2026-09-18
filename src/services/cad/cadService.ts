import { apiClient } from '../api/client';
import { MeshInspection, ValidationReport, NestResult } from '../../types';

function normalizeNestResult(data: any): NestResult {
  const sheets = (data.sheets || []).map((sheet: any, index: number) => ({
    sheet_index: sheet.sheet_number ?? sheet.sheet_index ?? index + 1,
    sheet_name: sheet.sheet_name || sheet.stock_sheet_name || `Sheet ${index + 1}`,
    parts_count: sheet.parts_count ?? (sheet.placed_parts || []).length,
    utilization: sheet.utilization ?? 0,
    dxf_path: sheet.dxf_path,
  }));

  return {
    output_dir: data.output_dir || '',
    total_parts_required: data.total_parts_required ?? 0,
    total_parts_placed: data.total_parts_placed ?? 0,
    total_parts_unplaced: data.total_parts_unplaced ?? 0,
    total_sheets_used: data.total_sheets_used ?? sheets.length,
    total_utilization: data.total_utilization ?? 0,
    total_waste: data.total_waste ?? 0,
    sheets,
  };
}

// ── inspect-3d deduplication cache ──────────────────────────────────────────
// Stores successful inspection results keyed by file path.
// Ensures the same STL is never inspected more than once per session.
const inspectionCache = new Map<string, MeshInspection>();

// Tracks in-flight requests so a second call for the same file
// while one is already running just awaits the same promise.
const inFlightInspections = new Map<string, Promise<MeshInspection>>();

export const cadService = {
  /**
   * Inspect a 3D STL file.
   * - Returns immediately from cache if the same path was already inspected.
   * - Deduplicates concurrent calls for the same path (returns the same promise).
   * - Supports AbortSignal to cancel when the file changes before the request finishes.
   */
  inspect3D: async (filePath: string, signal?: AbortSignal): Promise<MeshInspection> => {
    // 1. Return cached result if available
    const cached = inspectionCache.get(filePath);
    if (cached) {
      console.log(`[cadService] inspect3D cache hit: ${filePath}`);
      return cached;
    }

    // 2. Reuse in-flight request if one is already running for this path
    const inFlight = inFlightInspections.get(filePath);
    if (inFlight) {
      console.log(`[cadService] inspect3D awaiting in-flight request: ${filePath}`);
      return inFlight;
    }

    // 3. Fire new request
    const promise = (async (): Promise<MeshInspection> => {
      try {
        const res = await apiClient.get(
          `/cad/inspect-3d?file_path=${encodeURIComponent(filePath)}`,
          { signal }
        );
        const result: MeshInspection = res.data;
        // Only cache on success (not on abort/error)
        inspectionCache.set(filePath, result);
        return result;
      } catch (err: any) {
        // Do not cache errors or aborts
        throw err;
      } finally {
        inFlightInspections.delete(filePath);
      }
    })();

    inFlightInspections.set(filePath, promise);
    return promise;
  },

  /** Remove a path from the inspection cache (call after file replacement). */
  clearInspectionCache: (filePath?: string) => {
    if (filePath) {
      inspectionCache.delete(filePath);
    } else {
      inspectionCache.clear();
    }
  },

  parseDXF: async (filePath: string) => {
    const res = await apiClient.get(`/cad/parse-dxf?file_path=${encodeURIComponent(filePath)}`);
    return res.data;
  },
  parseDXFContent: async (dxfContent: string) => {
    const res = await apiClient.post('/cad/parse-dxf-content', {
      dxf_content: dxfContent
    });
    return res.data;
  },
  runNesting: async (
    partPaths: (string | {
      path?: string;
      dxf_content?: string;
      name?: string;
      quantity?: number;
      thickness?: number;
      priority?: string;
      priority_order?: number;
    })[],
    sheetWidth = 1200,
    sheetHeight = 600,
    spacing = 5,
    allowRotate = true,
    sheetThickness = 18
  ): Promise<NestResult> => {
    const res = await apiClient.post('/cad/nesting', {
      part_paths: partPaths.map((item) => {
        if (typeof item === 'string') {
          return {
            path: item,
            quantity: 1,
            thickness: sheetThickness,
          };
        }
        return {
          path: item.path || '',
          dxf_content: item.dxf_content,
          name: item.name,
          quantity: item.quantity ?? 1,
          thickness: item.thickness ?? sheetThickness,
          priority: item.priority ?? 'Normal',
          priority_order: item.priority_order ?? 100,
        };
      }),
      sheet_width: sheetWidth,
      sheet_height: sheetHeight,
      sheet_thickness: sheetThickness,
      spacing,
      allow_rotate: allowRotate,
    });
    return normalizeNestResult(res.data);
  },
  validateModel: async (filePath: string, toleranceMm = 0.1): Promise<ValidationReport> => {
    const res = await apiClient.post('/validation/model', {
      file_path: filePath,
      tolerance_mm: toleranceMm
    });
    return res.data;
  },
  validateManufacturing: async (filePath: string, toolDiameterMm = 3.175, maxDepthMm = 50.0): Promise<ValidationReport> => {
    const res = await apiClient.post('/validation/manufacturing', {
      file_path: filePath,
      tool_diameter_mm: toolDiameterMm,
      max_depth_mm: maxDepthMm
    });
    return res.data;
  },
  exportFile: async (inputFilePath: string, exportFormat: string): Promise<{ export_path: string; filename: string }> => {
    const res = await apiClient.post('/export', {
      input_file_path: inputFilePath,
      export_format: exportFormat
    });
    return res.data;
  },
  exportModel: async (inputFilePath: string, exportFormat: string, destPath?: string, options?: any) => {
    const res = await apiClient.post('/export', {
      input_file_path: inputFilePath,
      export_format: exportFormat,
      dest_path: destPath,
      options
    });
    return res.data;
  }
};
