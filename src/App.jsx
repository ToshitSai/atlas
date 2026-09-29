import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ResearchStartScreen from './components/ResearchStartScreen';
import ResearchChatWorkspace from './components/ResearchChatWorkspace';
import SettingsModal from './components/SettingsModal';
import { fetchProjects, fetchProjectDetails, sendChatMessage, sendDeepResearchStream, fetchSettings, approveDataset, fetchConversationMessages, fetchConversations } from './api';

// One conversation per project so the FIRST message (sent from the start
// screen) and every workspace follow-up share the same server-side memory.
function createConversationId() {
  return 'conv-' + (globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2));
}

function getConversationId(projectId) {
  if (!projectId) return createConversationId();
  const key = 'ai-scientist-conv-' + projectId;
  let conv = null;
  try { conv = localStorage.getItem(key); } catch (e) { /* private mode */ }
  if (!conv) {
    conv = 'conv-' + projectId + '-' + Math.random().toString(36).substring(2, 9);
    try { localStorage.setItem(key, conv); } catch (e) { /* ignore */ }
  }
  return conv;
}

function isLikelyDeepResearch(text) {
  const value = String(text || '').toLowerCase();
  return !/\b(just answer briefly|brief answer|don't research|do not research)\b/.test(value)
    && (/\b(deep research|investigate|literature review|research gap|analyze multiple papers|recent papers|design experiments|run experiments|error analysis|reproduce|benchmark|autonomous ml research|determine whether|statistically significant|significantly improve|performance degradation|experimentally|try several)\b/.test(value)
      || /\b(improve|optimi[sz]e|diagnose|figure out|find out)\b.*\b(model|fraud|recall|minority.class|detection|performance|overfitting|features?)\b/.test(value)
      || (/\b(dataset|datasets)\b.*\b(evaluate|experiment|test|benchmark)\b/.test(value) || /\bcompare\b.*\b(xgboost|random forest|models?|dataset|approach)\b/.test(value)));
}

export default function App() {
  const [projects, setProjects] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [activeProject, setActiveProject] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isLaunching, setIsLaunching] = useState(false);
  const [launchStartedAt, setLaunchStartedAt] = useState(null);
  const [launchShowsResearchActivity, setLaunchShowsResearchActivity] = useState(false);
  const [initialRequestActivities, setInitialRequestActivities] = useState([]);
  const [isApproving, setIsApproving] = useState(false);
  const [dockerReady, setDockerReady] = useState(false);
  const [llmConfigured, setLlmConfigured] = useState(false);
  // Research mode (AUTONOMOUS/GUIDED/MANUAL). Seeded from persisted app
  // settings; per-chat switches via the chat endpoint stay server-side.
  const [researchMode, setResearchMode] = useState('GUIDED');
  const [isInChatWorkspace, setIsInChatWorkspace] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  // Mobile sidebar drawer (<1024px): overlays the chat instead of squeezing it.
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Escape closes the drawer (and the settings modal keeps its own handling).
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') setIsSidebarOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Resizing up to the desktop breakpoint closes the drawer so the state never
  // goes stale (the drawer is CSS-hidden on desktop anyway).
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px)');
    const onChange = (e) => { if (e.matches) setIsSidebarOpen(false); };
    if (mq.addEventListener) mq.addEventListener('change', onChange);
    else mq.addListener(onChange);
    return () => {
      if (mq.removeEventListener) mq.removeEventListener('change', onChange);
      else mq.removeListener(onChange);
    };
  }, []);

  const loadProjects = async () => {
    const list = await fetchProjects();
    setProjects(list);
  };

  const loadConversations = async () => {
    const list = await fetchConversations();
    setConversations(list);
  };

  const loadSysSettings = async () => {
    const s = await fetchSettings();
    setDockerReady(s.dockerAvailable || false);
    setLlmConfigured(s.apiKeySet || false);
    if (s.researchMode) setResearchMode(s.researchMode);
  };

  useEffect(() => {
    loadProjects();
    loadConversations();
    loadSysSettings();
    const interval = setInterval(() => { loadProjects(); loadConversations(); }, 3000);
    return () => clearInterval(interval);
  }, []);

  // Sync active project state
  useEffect(() => {
    if (!activeProject?.id) return;
    const interval = setInterval(async () => {
      const updated = await fetchProjectDetails(activeProject.id);
      if (updated) {
        setActiveProject(updated);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [activeProject?.id]);

  const handleSendInitialChatMessage = async (userText) => {
    if (!userText.trim()) return;
    setIsLaunching(true);
    setLaunchStartedAt(Date.now());
    const showResearchActivity = isLikelyDeepResearch(userText);
    setLaunchShowsResearchActivity(showResearchActivity);
    setInitialRequestActivities([]);

    const requestId = createConversationId();
    const userMessageId = createConversationId();
    const userMsg = { id: userMessageId, requestId, role: 'user', content: userText };
    setChatMessages([userMsg]);
    setIsInChatWorkspace(true);

    // A fresh chat without an active project still gets its own conversation
    // id so follow-ups keep the same memory.
    const convId = conversationId || createConversationId();
    setConversationId(convId);
    try { localStorage.setItem('ai-scientist-active-conversation', convId); } catch (e) { /* private mode */ }

    try {
      const onActivity = (event) => setInitialRequestActivities(previous => {
        const existing = previous.findIndex(step => step.stage === event.stage);
        if (existing >= 0) return previous.map((step, index) => index === existing ? { ...step, ...event, id: step.id || `${requestId}-${event.stage}` } : step);
        return [...previous, { ...event, id: event.id || `${requestId}-${event.stage}` }];
      });
      const send = showResearchActivity ? sendDeepResearchStream : sendChatMessage;
      const res = await send(userText, activeProject?.id, convId, null, null, {
        requestId,
        messageId: userMessageId,
        researchMode
      }, [userMsg], onActivity);
      if (res.requestId !== requestId || res.responseToMessageId !== userMessageId) {
        throw new Error('The response could not be matched to the submitted message. Please retry.');
      }
      const assistantMsg = {
        id: res.messageId,
        conversationId: res.conversationId,
        requestId,
        responseToMessageId: res.responseToMessageId,
        role: 'assistant',
        content: res.response,
        intent: res.intent,
        action: res.action,
        datasets: res.candidates || null,
        recommendation: res.recommendation || null,
        researchQuery: res.researchQuery || null,
        selectionMode: res.selectionMode || null,
        selectedDataset: res.selectedDataset || null,
        activity: res.activity || []
      };
      setChatMessages(prev => [...prev, assistantMsg]);

      if (res.action === 'START_RESEARCH' && res.project) {
        setActiveProject(res.project);
        await loadProjects();
      }
    } catch (err) {
      setChatMessages(prev => [
        ...prev,
        { id: userMessageId + '-error', requestId, responseToMessageId: userMessageId, role: 'assistant', content: `Error: ${err.message}` }
      ]);
    } finally {
      await loadConversations();
      setIsLaunching(false);
      setLaunchStartedAt(null);
      setLaunchShowsResearchActivity(false);
      setInitialRequestActivities([]);
    }
  };

  const handleApproveDataset = async (repoId, researchQuery) => {
    if (!repoId || isApproving) return;
    setIsApproving(true);
    setIsInChatWorkspace(true);
    try {
      const res = await approveDataset(repoId, researchQuery || `Improve modeling on ${repoId}`);
      setChatMessages(prev => [
        ...prev,
        { id: Date.now() + 2, role: 'assistant', content: res.response || `Loading ${repoId}...` }
      ]);
      if (res.project) {
        const projId = res.project.id;
        setActiveProject(res.project);
        await loadProjects();
      }
    } catch (err) {
      setChatMessages(prev => [
        ...prev,
        { id: Date.now() + 2, role: 'assistant', content: `Sorry, I couldn't load that dataset: ${err.message}` }
      ]);
    } finally {
      await loadConversations();
      setIsApproving(false);
    }
  };

  const handleSelectConversation = async (conversation) => {
    setActiveProject(null);
    setIsInChatWorkspace(true);
    setConversationId(conversation.id);
    try { localStorage.setItem('ai-scientist-active-conversation', conversation.id); } catch (e) { /* private mode */ }
    setChatMessages([]);
    try {
      const msgs = await fetchConversationMessages(conversation.id);
      setChatMessages((msgs || []).map(m => ({
        id: m.id, role: m.role, content: m.content, intent: m.intent,
        datasets: null, recommendation: null, researchQuery: null, activity: []
      })));
    } catch (e) {
      setChatMessages([]);
    }
  };

  // Clicking a project in the sidebar: load its conversation history so the
  // chat survives page refreshes and switching between studies.
  const handleSelectProject = async (proj) => {
    setActiveProject(proj);
    setIsInChatWorkspace(true);
    const convId = getConversationId(proj.id);
    setConversationId(convId);
    setChatMessages([]);
    try {
      const msgs = await fetchConversationMessages(convId);
      const mapped = (msgs || []).map(m => ({
        id: m.id,
        role: m.role,
        content: m.content,
        intent: m.intent,
        datasets: null,
        recommendation: null,
        researchQuery: null
      }));
      setChatMessages(mapped);
    } catch (e) {
      setChatMessages([]);
    }
  };

  const handleNewResearchClick = () => {
    setActiveProject(null);
    setChatMessages([]);
    setIsInChatWorkspace(false);
    setConversationId(null);
    try { localStorage.removeItem('ai-scientist-active-conversation'); } catch (e) { /* private mode */ }
  };

  // Reopen the last selected persisted chat after a refresh. The list itself
  // remains the source of truth, so a deleted/unavailable id is ignored.
  useEffect(() => {
    if (conversationId || activeProject || !conversations.length) return;
    let savedId = null;
    try { savedId = localStorage.getItem('ai-scientist-active-conversation'); } catch (e) { /* private mode */ }
    const saved = conversations.find(item => item.id === savedId);
    if (saved) handleSelectConversation(saved);
  }, [conversations, conversationId, activeProject]);

  return (
    <div className="flex h-screen bg-[#0B0F17] text-slate-100 font-sans overflow-hidden">

      {/* Sakana Chat Style Left Sidebar — desktop rail / mobile drawer */}
      <Sidebar
        projects={projects}
        conversations={conversations}
        activeProject={activeProject}
        setActiveProject={handleSelectProject}
        activeConversationId={conversationId}
        onSelectConversation={handleSelectConversation}
        onNewResearch={handleNewResearchClick}
        onOpenSettings={() => setIsSettingsOpen(true)}
        dockerReady={dockerReady}
        llmConfigured={llmConfigured}
        isMobileOpen={isSidebarOpen}
        onMobileClose={() => setIsSidebarOpen(false)}
      />

      {/* Main Screen: Research Start Composer or Conversational Workspace.
          min-w-0 is essential: without it the flex child cannot shrink below
          its content width and the page overflows horizontally on phones. */}
      <main className="flex-1 min-w-0 flex flex-col h-screen overflow-hidden bg-[#0B0F17]">
        {!isInChatWorkspace && !activeProject ? (
          <ResearchStartScreen
            onSendChatMessage={handleSendInitialChatMessage}
            isLaunching={isLaunching}
            onOpenMenu={() => setIsSidebarOpen(true)}
          />
        ) : (
          <ResearchChatWorkspace
            activeProject={activeProject}
            setActiveProject={setActiveProject}
            onNewResearch={handleNewResearchClick}
            onOpenSettings={() => setIsSettingsOpen(true)}
            chatMessages={chatMessages}
            setChatMessages={setChatMessages}
            onApproveDataset={handleApproveDataset}
            isApproving={isApproving}
            conversationId={conversationId || getConversationId(activeProject?.id || 'general')}
            onConversationUpdated={loadConversations}
            initialRequestStartedAt={isLaunching && launchShowsResearchActivity ? launchStartedAt : null}
            initialRequestActivities={initialRequestActivities}
            onOpenMenu={() => setIsSidebarOpen(true)}
          />
        )}
      </main>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />

    </div>
  );
}
