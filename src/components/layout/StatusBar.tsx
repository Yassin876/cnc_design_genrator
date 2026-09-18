import React from 'react';

export const StatusBar: React.FC = () => {
  return (
    <footer className="h-7 bg-white border-t border-slate-200/90 flex items-center justify-start px-4 text-xs font-sans text-slate-500 select-none z-40 space-x-4">
      <div>
        <span className="text-slate-400">Units:</span> <span className="font-bold text-slate-700">mm</span>
      </div>

      <div className="h-3 w-px bg-slate-200" />

      <div>
        <span className="text-slate-400">Grid:</span> <span className="font-bold text-slate-700">10mm</span>
      </div>

      <div className="h-3 w-px bg-slate-200" />

      <div>
        <span className="text-slate-400">Objects:</span> <span className="font-bold text-slate-700">1</span>
      </div>

      <div className="h-3 w-px bg-slate-200" />

      <div className="flex items-center space-x-1.5 font-semibold text-emerald-600">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
        <span>GPU Available</span>
      </div>

      <div className="h-3 w-px bg-slate-200" />

      <div className="text-slate-400">
        Saved just now
      </div>
    </footer>
  );
};
