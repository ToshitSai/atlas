import React from 'react';

/**
 * Research Settings & Telemetry Modal.
 */
export default function SettingsModal({
  isOpen = false,
  onClose,
  settings = {},
  onSignOut,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 animate-panel-entrance" role="dialog" aria-modal="true">
      <div className="bg-[#181818] border border-[#303030] rounded-xl max-w-md w-full p-4 sm:p-5 space-y-4 shadow-2xl text-xs font-sans">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-[#303030] pb-2.5 font-sans">
          <h3 className="text-sm font-semibold text-[#E8E5DF] font-sans">
            Settings & Telemetry
          </h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="text-[#8A8884] hover:text-[#E8E5DF] p-1 rounded font-sans cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Settings & Telemetry Details */}
        <div className="space-y-3 font-sans">
          <div className="space-y-1 font-sans">
            <span className="text-[#8A8884] text-xs font-medium block font-sans">Execution Mode</span>
            <div className="p-2.5 rounded-lg bg-[#1B1B1B] border border-[#303030] text-[#E8E5DF] font-sans text-xs flex justify-between items-center">
              <span>{settings.sandboxMode || 'Process Sandbox (Subprocess isolation)'}</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-sans">Isolated</span>
            </div>
          </div>

          <div className="space-y-1 font-sans">
            <span className="text-[#8A8884] text-xs font-medium block font-sans">Effective Provider</span>
            <div className="p-2.5 rounded-lg bg-[#1B1B1B] border border-[#303030] text-[#E8E5DF] font-sans text-xs font-mono">
              {settings.llmEffectiveProvider || 'Heuristic / Rule-based Engine'}
            </div>
          </div>

          <div className="space-y-1 font-sans">
            <span className="text-[#8A8884] text-xs font-medium block font-sans">Academic Search</span>
            <div className="p-2.5 rounded-lg bg-[#1B1B1B] border border-[#303030] text-[#E8E5DF] font-sans text-xs">
              Semantic Scholar + OpenAlex Fallback
            </div>
          </div>

          <div className="flex items-center justify-between p-2.5 rounded-lg bg-[#1B1B1B] border border-[#303030] text-xs font-sans">
            <span className="text-[#8A8884] font-sans">System Version</span>
            <span className="font-mono text-[#F15A3A] font-semibold">v2.0</span>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="pt-2 border-t border-[#303030] flex items-center justify-between font-sans">
          {onSignOut ? (
            <button
              type="button"
              onClick={() => {
                onClose();
                onSignOut();
              }}
              className="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/30 font-semibold text-xs transition-colors cursor-pointer font-sans"
            >
              Sign Out
            </button>
          ) : <div />}
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-[#F15A3A] hover:bg-[#E44D31] text-white font-semibold text-xs btn-transition cursor-pointer font-sans"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
