import React from 'react';
import { useAiStore, STATUS_LOOKUP } from '../../app/store/useAiStore';
import { JobStageState } from '../../types';
import {
  Brain, Cpu, Wrench, CheckCircle2, XCircle, Clock,
  Zap, Layers, Loader2, RotateCcw, AlertTriangle
} from 'lucide-react';

const STAGES: { key: JobStageState; label: string; icon: React.FC<any> }[] = [
  { key: 'queued',              label: 'Queued',               icon: Clock },
  { key: 'processing',          label: 'Initializing',         icon: Cpu },
  { key: 'understanding',       label: 'AI Analysis',          icon: Brain },
  { key: 'generating',          label: 'Generating',           icon: Zap },
  { key: 'geometry_processing', label: 'Mesh Compiling',       icon: Layers },
  { key: 'optimizing',          label: 'Optimization',         icon: Wrench },
  { key: 'validating',          label: 'Validation',           icon: CheckCircle2 },
];

const STAGE_ORDER: JobStageState[] = STAGES.map(s => s.key);

function getStageIndex(stage: JobStageState) {
  const idx = STAGE_ORDER.indexOf(stage);
  return idx === -1 ? 0 : idx;
}

export const GenerationProgressPanel: React.FC = () => {
  const { 
    appStatus, 
    statusHeadline, 
    statusSubtext, 
    currentJobStage, 
    progressPercent, 
    stageMessage, 
    currentJobId, 
    errorMessage,
    setAppStatus 
  } = useAiStore();

  const isGeneratingOrProcessing = ['generating', 'processing', 'validating', 'loading', 'uploading', 'exporting'].includes(appStatus);
  const isFailed = appStatus === 'error' || currentJobStage === 'failed';
  const isCompleted = appStatus === 'success' || currentJobStage === 'completed';

  if (!isGeneratingOrProcessing && !isFailed && appStatus !== 'cancelled') {
    return null;
  }

  const currentIndex = getStageIndex(currentJobStage);

  return (
    <div className="absolute bottom-10 left-1/2 -translate-x-1/2 z-50 w-[660px] max-w-[92vw] font-sans">
      <div className="bg-white/95 backdrop-blur-md border border-slate-300 rounded-xl shadow-xl shadow-slate-900/10 overflow-hidden">
        {/* Header */}
        <div className={`px-5 py-3 flex items-center justify-between border-b ${
          isFailed ? 'bg-rose-50 border-rose-200' : isCompleted ? 'bg-emerald-50 border-emerald-200' : 'bg-indigo-50/80 border-indigo-100'
        }`}>
          <div className="flex items-center space-x-2.5">
            {isFailed ? (
              <XCircle className="w-4 h-4 text-rose-600" />
            ) : isCompleted ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            ) : (
              <Loader2 className="w-4 h-4 text-indigo-600 animate-spin" />
            )}
            <div>
              <h3 className="text-xs font-bold text-slate-900 font-mono">
                {statusHeadline}
              </h3>
              <p className="text-[11px] text-slate-500 font-mono">
                {stageMessage || statusSubtext}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2 font-mono">
            {currentJobId && (
              <span className="text-[10px] text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                Job #{currentJobId.slice(0, 8)}
              </span>
            )}
            {isFailed && (
              <button
                onClick={() => setAppStatus('empty')}
                className="px-2.5 py-1 bg-white border border-rose-200 text-rose-700 hover:bg-rose-50 rounded text-[11px] font-bold flex items-center space-x-1 transition-all"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Dismiss</span>
              </button>
            )}
          </div>
        </div>

        <div className="px-5 py-4 space-y-4">
          {/* Progress bar */}
          <div>
            <div className="flex justify-between text-[11px] font-mono text-slate-600 mb-1.5">
              <span>{stageMessage || `Processing Stage: ${currentJobStage}`}</span>
              <span className={isFailed ? 'text-rose-600 font-bold' : 'text-indigo-700 font-bold'}>
                {progressPercent}%
              </span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
              <div
                className={`h-full rounded-full transition-all duration-500 ease-out ${
                  isFailed
                    ? 'bg-rose-500'
                    : isCompleted
                    ? 'bg-emerald-500'
                    : 'bg-indigo-600'
                }`}
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {/* Pipeline Stepper */}
          <div className="flex items-center gap-1 pt-1">
            {STAGES.map((stage, idx) => {
              const isDone = idx < currentIndex || isCompleted;
              const isActive = idx === currentIndex && !isFailed && !isCompleted;
              const Icon = stage.icon;

              return (
                <React.Fragment key={stage.key}>
                  <div className="flex flex-col items-center gap-1 min-w-0 flex-1">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center border transition-all ${
                      isFailed && isActive
                        ? 'bg-rose-100 border-rose-500 text-rose-700'
                        : isActive
                        ? 'bg-indigo-600 border-indigo-700 text-white shadow-sm ring-2 ring-indigo-200'
                        : isDone
                        ? 'bg-emerald-100 border-emerald-400 text-emerald-700'
                        : 'bg-slate-50 border-slate-200 text-slate-400'
                    }`}>
                      {isDone ? (
                        <CheckCircle2 className="w-3.5 h-3.5" />
                      ) : isActive ? (
                        <Icon className="w-3.5 h-3.5 animate-pulse" />
                      ) : (
                        <Icon className="w-3 h-3" />
                      )}
                    </div>
                    <span className={`text-[9px] font-mono text-center leading-tight max-w-[56px] ${
                      isActive ? 'text-indigo-700 font-bold' : isDone ? 'text-emerald-700 font-semibold' : 'text-slate-400'
                    }`}>
                      {stage.label}
                    </span>
                  </div>
                  {idx < STAGES.length - 1 && (
                    <div className={`h-px flex-shrink-0 w-3 mt-[-12px] transition-colors ${
                      isDone ? 'bg-emerald-400' : isActive ? 'bg-indigo-400' : 'bg-slate-200'
                    }`} />
                  )}
                </React.Fragment>
              );
            })}
          </div>

          {/* Error detail banner if present */}
          {errorMessage && (
            <div className="p-2.5 bg-rose-50 border border-rose-200 rounded-md flex items-start space-x-2 text-xs font-mono text-rose-800">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Error Details: </span>
                <span>{errorMessage}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
