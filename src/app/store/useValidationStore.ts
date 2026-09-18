import { create } from 'zustand';
import { ValidationReport, ValidationIssue } from '../../types';

interface ValidationState {
  isValidating: boolean;
  validationReport: ValidationReport | null;
  selectedIssueId: string | null;
  toolDiameterMm: number;
  maxDepthMm: number;
  toleranceMm: number;

  // Actions
  setIsValidating: (loading: boolean) => void;
  setValidationReport: (report: ValidationReport | null) => void;
  selectIssue: (id: string | null) => void;
  setConstraintParams: (params: { toolDiameterMm?: number; maxDepthMm?: number; toleranceMm?: number }) => void;
  clearValidation: () => void;
}

export const useValidationStore = create<ValidationState>((set) => ({
  isValidating: false,
  validationReport: null,
  selectedIssueId: null,
  toolDiameterMm: 3.175,
  maxDepthMm: 50.0,
  toleranceMm: 0.1,

  setIsValidating: (isValidating) => set({ isValidating }),
  setValidationReport: (validationReport) => set({ validationReport, isValidating: false }),
  selectIssue: (selectedIssueId) => set({ selectedIssueId }),
  setConstraintParams: (params) => set((s) => ({
    toolDiameterMm: params.toolDiameterMm ?? s.toolDiameterMm,
    maxDepthMm: params.maxDepthMm ?? s.maxDepthMm,
    toleranceMm: params.toleranceMm ?? s.toleranceMm
  })),
  clearValidation: () => set({ validationReport: null, selectedIssueId: null, isValidating: false })
}));
