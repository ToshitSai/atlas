// Backend origin. Same-origin '/api' by default (the Vercel rewrite -> the
// serverless function). When VITE_API_BASE_URL is set (build-time), the UI
// calls an always-on FastAPI host instead — required for full research runs,
// because the serverless bundle deliberately excludes pandas/sklearn and a
// 30s function limit cannot host a multi-minute training pipeline.
const API_BASE = `${(import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')}/api`;
export const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

// Clerk's getToken() hook can only be called inside React. App registers the
// provider here so every API call (including SSE) carries the short-lived,
// verified session token without ever putting user IDs or secrets in storage.
let authTokenProvider = null;
export function setAuthTokenProvider(provider) {
  authTokenProvider = typeof provider === 'function' ? provider : null;
}

async function withAuthHeaders(headers = {}) {
  const next = new Headers(headers);
  if (authTokenProvider) {
    const token = await authTokenProvider();
    if (token) next.set('Authorization', `Bearer ${token}`);
  }
  return next;
}

async function safeFetchJson(url, options = {}) {
  try {
    const res = await fetch(url, { ...options, headers: await withAuthHeaders(options.headers) });
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
    return [];
  }
}

export async function fetchConversations() {
  try {
    return await safeFetchJson(`${API_BASE}/conversations`);
  } catch (err) {
    return [];
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
async function streamChat(body, { onActivity = () => {}, onToken = () => {} } = {}) {
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST', headers: await withAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body)
  });
  if (!response.ok || !response.body) throw new Error(`Server error (${response.status})`);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = ''; let finalResult = null;
  const consumeFrame = (frame) => {
    const kind = (frame.match(/^event:\s*(.+)$/m) || [])[1];
    const raw = (frame.match(/^data:\s*([\s\S]+)$/m) || [])[1];
    if (!raw) return;
    const data = JSON.parse(raw);
    if (kind === 'activity') onActivity(data);
    else if (kind === 'token') { if (data.text) onToken(data.text); }
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

export async function sendDeepResearchStream(message, projectId = null, conversationId = null, pendingAction = null, lastTopic = null, correlation = {}, conversationHistory = [], onActivity = () => {}, onToken = () => {}) {
  return streamChat(
    { message, projectId, conversationId, pendingAction, lastTopic, conversationHistory, ...correlation },
    { onActivity, onToken }
  );
}

// Normal-answer path over SSE so answer text renders token-by-token. The final
// frame still carries the authoritative, post-processed response for reconcile.
export async function sendChatStream(message, projectId = null, conversationId = null, { onToken = () => {}, onActivity = () => {} } = {}) {
  return streamChat(
    { message, projectId, conversationId, pendingAction: null, lastTopic: null, conversationHistory: [] },
    { onActivity, onToken }
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
