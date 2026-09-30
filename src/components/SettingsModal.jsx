import React from 'react';

/**
 * Research Settings Modal:
 * Functional modal for viewing configuration and telemetry with clean typography.
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
      <div className="bg-[#0B0B0B] border border-[#242424] rounded-xl max-w-md w-full p-4 sm:p-5 space-y-4 shadow-2xl text-xs font-sans">
        <div className="flex items-center justify-between border-b border-[#242424] pb-2.5 font-sans">
          <h3 className="text-sm font-semibold text-[#F4F4F6] font-sans flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#FF6500]" />
            Research Settings & Telemetry
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="text-[#8A8F98] hover:text-[#F4F4F6] p-1 rounded font-sans"
          >
            ✕
          </button>
        </div>

        <div className="space-y-3 font-sans">
          <div className="space-y-1 font-sans">
            <span className="text-[#8A8F98] text-xs font-medium block font-sans">Execution Mode</span>
            <div className="p-2.5 rounded-lg bg-[#101012] border border-[#242424] text-[#F4F4F6] font-sans text-xs">
              {settings.sandboxMode || 'Process Sandbox (Subprocess isolation)'}
            </div>
          </div>

          <div className="space-y-1 font-sans">
            <span className="text-[#8A8F98] text-xs font-medium block font-sans">Effective Provider</span>
            <div className="p-2.5 rounded-lg bg-[#101012] border border-[#242424] text-[#F4F4F6] font-sans text-xs">
              {settings.llmEffectiveProvider || 'Heuristic / Rule-based Engine'}
            </div>
          </div>

          <div className="space-y-1 font-sans">
            <span className="text-[#8A8F98] text-xs font-medium block font-sans">Academic Search</span>
            <div className="p-2.5 rounded-lg bg-[#101012] border border-[#242424] text-[#F4F4F6] font-sans text-xs">
              Semantic Scholar + OpenAlex Fallback
            </div>
          </div>
        </div>

        <div className="pt-2 border-t border-[#242424] flex justify-end font-sans">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-[#FF6500] hover:bg-[#FF302A] text-white font-semibold text-xs btn-transition cursor-pointer font-sans"
          >
            Close Settings
          </button>
        </div>
      </div>
    </div>
  );
}
