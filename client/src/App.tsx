import React, { useEffect, useState } from 'react';
import { getDocuments, deleteDocument, DocumentInfo } from './api';
import UploadZone from './components/UploadZone';
import Chat from './components/Chat';

function App() {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);

  // Fetch the document list from Flask and store it in state
  async function loadDocs() {
    setDocs(await getDocuments());
  }

  // Load once when the page opens
  useEffect(() => { loadDocs(); }, []);

  async function handleDelete(id: number) {
    await deleteDocument(id);
    loadDocs();   // refresh the list after deleting
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">SnapRAG</h1>

        {/* After an upload finishes, UploadZone calls loadDocs to refresh */}
        <UploadZone onUploaded={loadDocs} />

        <h2 className="text-lg font-semibold mt-8 mb-3 text-gray-300">Documents</h2>
        <div className="space-y-2">
          {docs.map(d => (
            <div key={d.id} className="flex justify-between items-center bg-gray-900 border border-gray-800 rounded-lg px-4 py-3">
              <span>{d.filename} <span className="text-gray-500 text-sm">({d.chunk_count} chunks)</span></span>
              <button onClick={() => handleDelete(d.id)} className="text-gray-500 hover:text-red-400">✕</button>
            </div>
          ))}
          {docs.length === 0 && <p className="text-gray-500">No documents yet.</p>}
        </div>
        <h2 className="text-lg font-semibold mt-8 mb-3 text-gray-300">Chat</h2>
        <Chat />
      </div>
    </div>
  );
}

export default App;