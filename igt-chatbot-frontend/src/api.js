export async function apiLogin(email, password) {
  const res = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  return await res.json();
}

export async function apiRegister(email, name, dob, password) {
  const res = await fetch('/api/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, name, dob, password })
  });
  return await res.json();
}
const API_BASE = 'http://localhost:5000'; // Adjust if needed

// Helper to handle cookies for session
const fetchWithCreds = (url, options = {}) =>
  fetch(url, { ...options, credentials: 'include' });

export async function loginUser(email, password) {
  // Your backend expects only email, so password is ignored
  const form = new FormData();
  form.append('email', email);
  form.append('action', 'Login');
  const res = await fetchWithCreds(`${API_BASE}/`, {
    method: 'POST',
    body: form
  });
  if (res.ok) return { success: true };
  return { success: false, error: 'Invalid email or server error' };
}

export async function registerUser(email, password) {
  // No register endpoint in backend, so simulate success
  // You may want to implement this in Flask
  return { success: true };
}

// Send chat message to backend (JSON API)
export async function sendMessage(payload) {
  const res = await fetchWithCreds(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    return { answer: data.error || 'Error from server.' };
  }
  const data = await res.json();
  return { answer: data.answer, answer_html: data.answer_html };
}

// Upload files to backend (JSON API)
export async function uploadFiles(files) {
  const form = new FormData();
  for (let i = 0; i < files.length; i++) {
    form.append('files', files[i]);
  }
  const res = await fetchWithCreds(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: form
  });
  if (!res.ok) return { success: false };
  const data = await res.json();
  return { success: true, uploaded: data.uploaded };
}

// Fetch chat history from backend (JSON API)
export async function getChatHistory() {
  const res = await fetchWithCreds(`${API_BASE}/api/history`);
  if (!res.ok) return [];
  const data = await res.json();
  if (!data.history) return [];
  // Flatten to [{role, content}]
  return data.history.map(pair => [
    { role: 'user', content: pair.user },
    { role: 'assistant', content: pair.assistant }
  ]).flat();
}

// Start a new chat (archive current)
export async function startNewChat() {
  const res = await fetchWithCreds(`${API_BASE}/api/new_chat`, {
    method: 'POST',
  });
  return await res.json();
}

// Fetch all previous chats (metadata only)
export async function getChatsHistory() {
  const res = await fetchWithCreds(`${API_BASE}/api/chats_history`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.chats_history || [];
}

// Fetch a specific previous chat by index
export async function getChatByIndex(idx) {
  const res = await fetchWithCreds(`${API_BASE}/api/chats_history/${idx}`);
  if (!res.ok) return null;
  const data = await res.json();
  return data;
}


// Fetch uploaded files for context selection
export async function getUploadedFiles() {
  const res = await fetchWithCreds(`${API_BASE}/api/files`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.files || [];
}
