import React, { useEffect, useState } from 'react';
import { getDocuments, DocumentInfo } from './api';

function App() {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [error, setError] = useState('');

  // Runs once when the page loads
  useEffect(() => {
    getDocuments()
      .then(setDocs)
      .catch(() => setError('Could not reach Flask on port 5001'));
  }, []);

  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">
      <h1 className="text-3xl font-bold mb-4">SnapRAG</h1>
      {error && <p className="text-red-400">{error}</p>}
      {docs.map(d => (
        <p key={d.id}>{d.filename} ({d.chunk_count} chunks)</p>
      ))}
    </div>
  );
}

export default App;