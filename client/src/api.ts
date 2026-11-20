import axios from 'axios';

// Base URL of the Flask server (port 5001, since 5000 is taken by AirPlay on Mac)
const API = 'http://127.0.0.1:5001/api';

// ─── Types: the shape of the JSON Flask returns ──────────────────────────────
export interface DocumentInfo {
  id: number;
  filename: string;
  file_type: string;   // 'pdf' or 'image'
  chunk_count: number;
  created_at: string;
}

export interface Source {
  filename: string;
  similarity: number;  // 0 to 1, how close the chunk was to the question
  preview: string;     // first 150 characters of the chunk
}

export interface AskResponse {
  answer: string;
  sources: Source[];
}

// ─── GET /api/documents/ ─────────────────────────────────────────────────────
export async function getDocuments(): Promise<DocumentInfo[]> {
  const res = await axios.get(`${API}/documents/`);
  return res.data;
}

// ─── POST /api/documents/upload ──────────────────────────────────────────────
// Files must be sent as FormData (multipart), the same as curl's -F "file=@..."
export async function uploadDocument(file: File) {
  const form = new FormData();
  form.append('file', file);   // 'file' must match request.files['file'] in Flask
  const res = await axios.post(`${API}/documents/upload`, form);
  return res.data;
}

// ─── DELETE /api/documents/<id> ──────────────────────────────────────────────
export async function deleteDocument(id: number) {
  await axios.delete(`${API}/documents/${id}`);
}

// ─── POST /api/chat/ask ──────────────────────────────────────────────────────
export async function askQuestion(question: string): Promise<AskResponse> {
  const res = await axios.post(`${API}/chat/ask`, { question });
  return res.data;
}