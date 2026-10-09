// Backend origin. Same-origin '/api' by default (the Vercel rewrite -> the
// serverless function). When VITE_API_BASE_URL is set (build-time), the UI
// calls an always-on FastAPI host instead — required for full research runs,
// because the serverless bundle deliberately excludes pandas/sklearn and a
// 30s function limit cannot host a multi-minute training pipeline.
const API_BASE = `${(import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')}/api`;
export const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

const LOCAL_HISTORY_DB = 'atlas-history';
function openLocalHistory() {
  if (!('indexedDB' in globalThis)) return Promise.reject(new Error('IndexedDB unavailable'));
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(LOCAL_HISTORY_DB, 1);
    request.onupgradeneeded = () => request.result.createObjectStore('chats', { keyPath: 'id' });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
async function localHistoryAll() {
  const db = await openLocalHistory();
  return new Promise((resolve, reject) => { const req = db.transaction('chats').objectStore('chats').getAll(); req.onsuccess = () => resolve(req.result || []); req.onerror = () => reject(req.error); });
}
export async function saveLocalConversation(chat) {
  const db = await openLocalHistory();
  return new Promise((resolve, reject) => { const req = db.transaction('chats', 'readwrite').objectStore('chats').put(chat); req.onsuccess = () => resolve(chat); req.onerror = () => reject(req.error); });
}

// Accounts/auth were removed. The server issues an anonymous HttpOnly session
// cookie and namespaces data by it; requests only need to send cookies along
// (credentials: 'include'), never an Authorization header.
async function safeFetchJson(url, options = {}) {
  try {
    const res = await fetch(url, { credentials: 'include', ...options, headers: options.headers });
    const rawText = await res.text();
    let data;

    try {
      data = JSON.parse(rawText);
    } catch (e) {
      console.error(`[API NON-JSON RESPONSE] Status: ${res.status}, Raw text:`, rawText.slice(0, 200));
      throw new Error(`Server returned non-JSON response (Status ${res.status}): ${rawText.slice(0, 120)}`);
    }

    if (!res.ok) {
      const msg = data.error || data.detail || data.message || `Server error (${res.status})`;
      throw new Error(msg);
    }

    return data;
  } catch (err) {
    console.error(`[API FETCH FAILED] ${url}:`, err.message);
    throw err;
  }
}

export async function fetchHealth() {
  return safeFetchJson(`${API_BASE}/health`);
}

export async function fetchConfig() {
  return safeFetchJson(`${API_BASE}/config`);
}

export async function fetchSettings() {
  try {
    return await safeFetchJson(`${API_BASE}/settings`);
  } catch (err) {
    return { llmProvider: "Not configured", dockerAvailable: false };
  }
}

export async function updateSettings(settings) {
  return safeFetchJson(`${API_BASE}/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings)
  });
}

export async function fetchConversationMessages(conversationId) {
  try {
    return await safeFetchJson(`${API_BASE}/conversations/${conversationId}/messages`);
  } catch (err) {
    try { return (await localHistoryAll()).find((chat) => chat.id === conversationId)?.messages || []; } catch { return []; }
  }
}

export async function checkAnswerConfidence(answer, sources = [], question = '') {
  return safeFetchJson(`${API_BASE}/confidence/check`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answer, sources, question })
  });
}

export async function fetchConversations() {
  try {
    return await safeFetchJson(`${API_BASE}/conversations`);
  } catch (err) {
    try { return localHistoryAll(); } catch { return []; }
  }
}

export async function fetchProjects() {
  try {
    return await safeFetchJson(`${API_BASE}/projects`);
  } catch (err) {
    return [];
  }
}

export async function fetchProjectDetails(id) {
  try {
    return await safeFetchJson(`${API_BASE}/projects/${id}`);
  } catch (err) {
    return null;
  }
}

export async function createResearchProject(formData) {
  return safeFetchJson(`${API_BASE}/research`, {
    method: 'POST',
    body: formData
  });
}

export async function sendChatMessage(message, projectId = null, conversationId = null, pendingAction = null, lastTopic = null, correlation = {}, conversationHistory = []) {
  return safeFetchJson(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, projectId, conversationId, pendingAction, lastTopic, conversationHistory, ...correlation })
  });
}

// Shared SSE reader for /api/chat/stream. Emits three frame kinds:
//   activity -> onActivity(data)   (real planner/retrieval/synthesis steps)
//   token    -> onToken(text)      (incremental answer text from the provider)
//   final    -> resolves with the authoritative result dict
//   error    -> rejects
async function streamChat(body, { onActivity = () => {}, onToken = () => {}, signal } = {}) {
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
    ,signal
  });
  if (!response.ok || !response.body) {
    let detail = '';
    try { detail = (await response.clone().text()).slice(0, 500); } catch { detail = ''; }
    console.error('[API STREAM ERROR]', { status: response.status, body: detail });
    let message = `Server error (${response.status})`;
    try {
      const parsed = JSON.parse(detail);
      message = parsed.detail || parsed.error || parsed.message || message;
    } catch { /* keep status-only message for non-JSON responses */ }
    throw new Error(message);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = ''; let finalResult = null;
  const consumeFrame = (frame) => {
    const kind = (frame.match(/^event:\s*(.+)$/m) || [])[1];
    const raw = (frame.match(/^data:\s*([\s\S]+)$/m) || [])[1];
    if (!raw) return;
    const data = JSON.parse(raw);
    if (kind === 'activity' || ['plan','search_start','search_result','read_source','source_checked','synthesizing','verifying','progress'].includes(kind)) onActivity(data);
    else if (kind === 'token' || kind === 'answer_delta') { if (data.text) onToken(data.text); }
    else if (kind === 'sources') onActivity({ ...data, stage: 'sources', status: 'completed', eventType: kind });
    else if (kind === 'final') finalResult = data;
    else if (kind === 'error') throw new Error(data.error || 'Stream failed');
  };
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split('\n\n'); buffer = frames.pop() || '';
    frames.forEach(consumeFrame);
  }
  // A proxy/serverless runtime can close immediately after the final event;
  // consume a valid unterminated final frame instead of reporting a false error.
  buffer += decoder.decode();
  if (buffer.trim()) consumeFrame(buffer);
  if (!finalResult) throw new Error('Stream ended without a final response.');
  return finalResult;
}

export async function sendDeepResearchStream(message, projectId = null, conversationId = null, pendingAction = null, lastTopic = null, correlation = {}, conversationHistory = [], onActivity = () => {}, onToken = () => {}, signal = undefined) {
  return streamChat(
    { message, projectId, conversationId, pendingAction, lastTopic, conversationHistory, ...correlation },
    { onActivity, onToken, signal }
  );
}

// Normal-answer path over SSE so answer text renders token-by-token. The final
// frame still carries the authoritative, post-processed response for reconcile.
export async function sendChatStream(message, projectId = null, conversationId = null, { onToken = () => {}, onActivity = () => {}, conversationHistory = [], correlation = {}, signal, variation = false, previousAnswer = '' } = {}) {
  return streamChat(
    { message, projectId, conversationId, pendingAction: null, lastTopic: null, conversationHistory, variation, previousAnswer, ...correlation },
    { onActivity, onToken, signal }
  );
}

export async function sendControlSignal(projectId, signal) {
  return safeFetchJson(`${API_BASE}/projects/${projectId}/control`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ signal })
  });
}

export async function searchDatasets(query, limit = 6) {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return safeFetchJson(`${API_BASE}/datasets/search?${params.toString()}`);
}

export async function inspectDataset(urlOrRepoId) {
  return safeFetchJson(`${API_BASE}/datasets/inspect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: urlOrRepoId })
  });
}

export async function approveDataset(repoId, researchQuery, opts = {}) {
  return safeFetchJson(`${API_BASE}/datasets/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      repoId,
      researchQuery,
      budget: opts.budget ?? 60,
      maxExperiments: opts.maxExperiments ?? 5
    })
  });
}

export async function fetchProjectDataset(id) {
  try {
    return await safeFetchJson(`${API_BASE}/projects/${id}/dataset`);
  } catch (err) {
    return null;
  }
}

export async function fetchProjectBaselines(id) {
  try {
    return await safeFetchJson(`${API_BASE}/projects/${id}/baselines`);
  } catch (err) {
    return [];
  }
}

export async function fetchProjectTree(id) {
  try {
    return await safeFetchJson(`${API_BASE}/projects/${id}/tree`);
  } catch (err) {
    return [];
  }
}

export async function fetchProjectErrorAnalysis(id) {
  try {
    return await safeFetchJson(`${API_BASE}/projects/${id}/error-analysis`);
  } catch (err) {
    return null;
  }
}

export async function fetchProjectLiterature(id) {
  try {
    return await safeFetchJson(`${API_BASE}/projects/${id}/literature`);
  } catch (err) {
    return [];
  }
}

export async function fetchProjectReport(id) {
  try {
    const data = await safeFetchJson(`${API_BASE}/projects/${id}/report`);
    return data ? data.report : null;
  } catch (err) {
    return null;
  }
}

// Structured research state (§14): the single endpoint that serves the full
// researchSession/goal/questions/literature/datasets/hypotheses/experiments/
// results/analysis/pipeline/reasoning shape. The workspace currently derives
// the same view client-side from the per-artifact endpoints; this keeps the
// server-side structured state available to any client (mobile, API, tests).
export async function fetchResearchState(id) {
  try {
    return await safeFetchJson(`${API_BASE}/projects/${id}/research-state`);
  } catch (err) {
    return null;
  }
}
