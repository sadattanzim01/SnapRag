import axios from 'axios';

const API = 'http://127.0.0.1:5001/api';

export interface DocumentInfo {
  id: number;
  filename: string;
  file_type: string;
  chunk_count: number;
  created_at: string;
}

export interface Source {
  filename: string;
  similarity: number;
  preview: string;
}

// A document Claude wrote for the user. Shown in the right panel.
export interface GeneratedDoc {
  title: string;
  content: string;   // Markdown
}

export interface AskResponse {
  answer: string;
  sources: Source[];
  document: GeneratedDoc | null;   // null for ordinary answers
}

// One earlier message, sent so Claude remembers the conversation
export interface HistoryItem {
  role: 'user' | 'assistant';
  content: string;
}

export async function getDocuments(): Promise<DocumentInfo[]> {
  const res = await axios.get(`${API}/documents/`);
  return res.data;
}

export async function uploadDocument(file: File) {
  const form = new FormData();
  form.append('file', file);
  const res = await axios.post(`${API}/documents/upload`, form);
  return res.data;
}

export async function deleteDocument(id: number) {
  await axios.delete(`${API}/documents/${id}`);
}

// URL of the original uploaded file, used by the viewer panel
export function fileUrl(id: number): string {
  return `${API}/documents/${id}/file`;
}

// documentIds limits the search to the documents ticked in the sidebar
export async function askQuestion(
  question: string,
  documentIds: number[],
  history: HistoryItem[]
): Promise<AskResponse> {
  const res = await axios.post(`${API}/chat/ask`, {
    question,
    document_ids: documentIds,
    history,
  });
  return res.data;
}