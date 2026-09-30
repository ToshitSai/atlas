import React from 'react';

/**
 * Research Settings Modal:
 * Functional modal for viewing configuration and telemetry.
 */
export default function SettingsModal({
  isOpen = false,
  onClose,
  settings = {},
  onSaveSettings,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 animate-panel-entrance" role="dialog" aria-modal="true">
      <div className="bg-[#0B0B0B] border border-[#242424] rounded-lg max-w-md w-full p-4 sm:p-5 space-y-4 shadow-2xl text-xs font-sans">
        <div className="flex items-center justify-between border-b border-[#242424] pb-2.5">
          <h3 className="text-sm font-mono font-bold text-[#F4F4F6] uppercase flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#FF6500]" />
            Research Settings & Telemetry
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="text-[#8A8F98] hover:text-[#F4F4F6] p-1 rounded"
          >
            ✕
          </button>
        </div>

        <div className="space-y-3">
          <div className="space-y-1">
            <span className="text-[#8A8F98] font-mono text-[10px] uppercase">Execution Mode</span>
            <div className="p-2 rounded bg-[#101012] border border-[#242424] text-[#F4F4F6] font-mono">
              {settings.sandboxMode || 'Process Sandbox (Subprocess isolation)'}
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-[#8A8F98] font-mono text-[10px] uppercase">Effective Provider</span>
            <div className="p-2 rounded bg-[#101012] border border-[#242424] text-[#F4F4F6] font-mono">
              {settings.llmEffectiveProvider || 'Heuristic / Rule-based Engine'}
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-[#8A8F98] font-mono text-[10px] uppercase">Academic Search</span>
            <div className="p-2 rounded bg-[#101012] border border-[#242424] text-[#F4F4F6] font-mono">
              Semantic Scholar + OpenAlex Fallback
            </div>
          </div>
        </div>

        <div className="pt-2 border-t border-[#242424] flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-[#FF6500] hover:bg-[#FF302A] text-white font-semibold text-xs btn-transition cursor-pointer"
          >
            Close Settings
          </button>
        </div>
      </div>
    </div>
  );
}
