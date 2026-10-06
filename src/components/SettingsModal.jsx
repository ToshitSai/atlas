import React, { useState } from 'react';

/**
 * User Profile & Research Settings Modal:
 * Tabbed modal allowing switching between User Profile details and Research Settings/Telemetry.
 */
function getInitials(name) {
  if (!name || typeof name !== 'string') return 'US';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export default function SettingsModal({
  isOpen = false,
  onClose,
  settings = {},
  onSaveSettings,
  onSignOut,
  userProfile = {},
  onUpdateUserProfile,
}) {
  const [activeTab, setActiveTab] = useState('profile'); // 'profile' | 'settings'
  const [editedName, setEditedName] = useState(userProfile.name || 'Toshit Sai Galam');
  const [isEditingName, setIsEditingName] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  // Sync state when profile prop changes
  React.useEffect(() => {
    setEditedName(userProfile.name || 'Toshit Sai Galam');
  }, [userProfile.name]);

  if (!isOpen) return null;

  const handleSaveUsername = (e) => {
    e?.preventDefault();
    if (!editedName.trim()) return;
    if (onUpdateUserProfile) {
      onUpdateUserProfile({ name: editedName.trim() });
    }
    setIsEditingName(false);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 animate-panel-entrance" role="dialog" aria-modal="true">
      <div className="bg-[#181818] border border-[#303030] rounded-xl max-w-md w-full p-4 sm:p-5 space-y-4 shadow-2xl text-xs font-sans">
        {/* Modal Navigation Bar / Tabs */}
        <div className="flex items-center justify-between border-b border-[#303030] pb-2.5 font-sans">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveTab('profile')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors font-sans cursor-pointer ${
                activeTab === 'profile'
                  ? 'bg-[#F15A3A]/15 text-[#F15A3A] border border-[#F15A3A]/40 font-semibold'
                  : 'text-[#8A8884] hover:text-[#E8E5DF] hover:bg-[#1B1B1B]'
              }`}
            >
              User Profile
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('settings')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors font-sans cursor-pointer ${
                activeTab === 'settings'
                  ? 'bg-[#F15A3A]/15 text-[#F15A3A] border border-[#F15A3A]/40 font-semibold'
                  : 'text-[#8A8884] hover:text-[#E8E5DF] hover:bg-[#1B1B1B]'
              }`}
            >
              Settings & Telemetry
            </button>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="text-[#8A8884] hover:text-[#E8E5DF] p-1 rounded font-sans cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Tab 1: User Profile View */}
        {activeTab === 'profile' && (
          <div className="space-y-4 font-sans">
            <div className="flex items-center gap-3.5 p-3 rounded-xl bg-[#1B1B1B] border border-[#303030]">
              <div className="relative shrink-0">
                <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-[#F15A3A] to-[#FF9100] flex items-center justify-center font-bold text-sm text-white shadow-md border border-[#F15A3A]/40 font-sans">
                  {getInitials(userProfile.name || editedName)}
                </div>
                <span className="absolute bottom-0 right-0 w-3 h-3 rounded-full bg-emerald-500 border-2 border-[#1B1B1B]" title="Active" />
              </div>
              <div className="min-w-0 flex-1 font-sans">
                <div className="flex items-center justify-between gap-2">
                  <h4 className="text-sm font-semibold text-[#E8E5DF] truncate font-sans">
                    {userProfile.name || 'Research User'}
                  </h4>
                  <button
                    type="button"
                    onClick={() => setIsEditingName(!isEditingName)}
                    className="text-[11px] px-2 py-0.5 rounded bg-[#F15A3A]/15 text-[#F15A3A] hover:bg-[#F15A3A]/25 border border-[#F15A3A]/40 font-semibold cursor-pointer font-sans transition-colors shrink-0"
                  >
                    {isEditingName ? 'Cancel' : 'Edit Name'}
                  </button>
                </div>
                <p className="text-xs text-[#8A8884] truncate font-sans mt-0.5">
                  {userProfile.email || 'researcher@institution.edu'}
                </p>
                <span className="text-[11px] text-[#F15A3A] font-medium block mt-1 font-sans">
                  {userProfile.role || 'Lead ML Researcher'}
                </span>
              </div>
            </div>

            {/* Editable Username Form */}
            {isEditingName && (
              <form onSubmit={handleSaveUsername} className="p-3 rounded-xl bg-[#222222] border border-[#F15A3A]/40 space-y-2 font-sans animate-fadeIn">
                <label className="text-[11px] font-semibold text-[#E8E5DF] block font-sans">
                  Edit Display Username
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={editedName}
                    onChange={(e) => setEditedName(e.target.value)}
                    placeholder="Enter new username"
                    className="flex-1 bg-[#141414] border border-[#404040] focus:border-[#F15A3A] rounded-lg px-2.5 py-1.5 text-xs text-[#E8E5DF] outline-none font-sans"
                    autoFocus
                  />
                  <button
                    type="submit"
                    className="px-3 py-1.5 rounded-lg bg-[#F15A3A] hover:bg-[#E44D31] text-white font-semibold text-xs cursor-pointer font-sans transition-colors"
                  >
                    Save
                  </button>
                </div>
              </form>
            )}

            {savedSuccess && (
              <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs text-center font-medium font-sans">
                ✓ Username updated successfully!
              </div>
            )}

            <div className="grid grid-cols-2 gap-2 font-sans">
              <div className="p-2.5 rounded-lg bg-[#1B1B1B] border border-[#303030] space-y-0.5">
                <span className="text-[10px] text-[#8A8884] uppercase tracking-wider block font-sans">Organization</span>
                <span className="text-xs font-medium text-[#E8E5DF] block truncate font-sans">AutoML Research Lab</span>
              </div>
              <div className="p-2.5 rounded-lg bg-[#1B1B1B] border border-[#303030] space-y-0.5">
                <span className="text-[10px] text-[#8A8884] uppercase tracking-wider block font-sans">Session Status</span>
                <span className="text-xs font-medium text-emerald-400 flex items-center gap-1 font-sans">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Connected
                </span>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-[#1B1B1B] border border-[#303030] space-y-2 font-sans">
              <span className="text-xs font-semibold text-[#E8E5DF] block font-sans">Research Activity Overview</span>
              <div className="grid grid-cols-3 gap-2 text-center font-sans">
                <div className="p-2 rounded bg-[#1B1B1B] border border-[#303030]">
                  <span className="text-sm font-bold text-[#F15A3A] block font-sans">24</span>
                  <span className="text-[10px] text-[#8A8884] font-sans">Experiments</span>
                </div>
                <div className="p-2 rounded bg-[#1B1B1B] border border-[#303030]">
                  <span className="text-sm font-bold text-[#E8E5DF] block font-sans">142</span>
                  <span className="text-[10px] text-[#8A8884] font-sans">Papers Cited</span>
                </div>
                <div className="p-2 rounded bg-[#1B1B1B] border border-[#303030]">
                  <span className="text-sm font-bold text-emerald-400 block font-sans">99.4%</span>
                  <span className="text-[10px] text-[#8A8884] font-sans">Accuracy</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Settings & Telemetry View */}
        {activeTab === 'settings' && (
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
        )}

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
