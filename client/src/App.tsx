import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Copy, Download, FileText, X } from 'lucide-react';
import { getDocuments, deleteDocument, DocumentInfo, GeneratedDoc } from './api';
import UploadZone from './components/UploadZone';
import Chat from './components/Chat';
import DocViewer from './components/DocViewer';

function App() {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  // Documents the chat is allowed to search (ticked checkboxes)
  const [selected, setSelected] = useState<Set<number>>(new Set());
  // Document Claude generated, shown in the right panel
  const [generated, setGenerated] = useState<GeneratedDoc | null>(null);
  // Document being previewed in the viewer panel next to the sidebar
  const [viewingId, setViewingId] = useState<number | null>(null);

  const knownIds = useRef<Set<number>>(new Set());

  async function loadDocs() {
    const list = await getDocuments();
    setDocs(list);

    const prevKnown = knownIds.current;
    knownIds.current = new Set(list.map(d => d.id));

    setSelected(prev => {
      const next = new Set<number>();
      for (const d of list) {
        if (prev.has(d.id) || !prevKnown.has(d.id)) next.add(d.id);
      }
      return next;
    });
  }

  useEffect(() => { loadDocs(); }, []);

  async function handleDelete(id: number) {
    await deleteDocument(id);
    if (viewingId === id) setViewingId(null);   // close the viewer if its file is gone
    loadDocs();
  }

  function toggle(id: number) {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  const allSelected = docs.length > 0 && selected.size === docs.length;
  function toggleAll() {
    setSelected(allSelected ? new Set() : new Set(docs.map(d => d.id)));
  }

  // Derived from the id, so it always reflects the latest document list
  const viewing = docs.find(d => d.id === viewingId) || null;

  function copyDoc() {
    if (generated) navigator.clipboard.writeText(generated.content);
  }

  function downloadDoc() {
    if (!generated) return;
    const blob = new Blob([generated.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${generated.title}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="h-screen flex bg-gray-950 text-white">

      {/* ── LEFT: upload + document list ─────────────────────────────────── */}
      <aside className="w-72 shrink-0 border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <h1 className="text-2xl font-bold">SnapRAG</h1>
        </div>

        <div className="p-4">
          <UploadZone onUploaded={loadDocs} />
        </div>

        <div className="px-4 flex items-center justify-between text-sm text-gray-400">
          <span>{selected.size} of {docs.length} selected</span>
          <button onClick={toggleAll} className="hover:text-white">
            {allSelected ? 'Select none' : 'Select all'}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {docs.map(d => (
            <div
              key={d.id}
              className={`flex items-center gap-2 border rounded-lg px-3 py-2 ${
                viewingId === d.id ? 'bg-gray-800 border-blue-500' : 'bg-gray-900 border-gray-800'
              }`}
            >
              <input
                type="checkbox"
                checked={selected.has(d.id)}
                onChange={() => toggle(d.id)}
                className="accent-blue-500"
              />
              {/* Clicking the name opens the viewer; the checkbox only changes chat scope */}
              <button
                onClick={() => setViewingId(d.id)}
                className="flex flex-1 items-center gap-2 min-w-0 text-left hover:text-blue-400"
                title={`Open ${d.filename}`}
              >
                <FileText size={16} className="text-gray-500 shrink-0" />
                <span className="truncate text-sm">{d.filename}</span>
              </button>
              <button onClick={() => handleDelete(d.id)} className="text-gray-500 hover:text-red-400">
                <X size={16} />
              </button>
            </div>
          ))}
          {docs.length === 0 && <p className="text-gray-500 text-sm">No documents yet.</p>}
        </div>
      </aside>

      {/* ── VIEWER: original file preview (only when one is open) ────────── */}
      {viewing && <DocViewer doc={viewing} onClose={() => setViewingId(null)} />}

      {/* ── MIDDLE: chat. min-w keeps it usable when several panels are open ─ */}
      <main className="flex-1 min-w-[24rem]">
        <Chat selectedIds={Array.from(selected)} onDocument={setGenerated} />
      </main>

      {/* ── RIGHT: generated document ────────────────────────────────────── */}
      {generated && (
        <section className="w-[28rem] shrink-0 border-l border-gray-800 flex flex-col">
          <div className="flex items-center gap-2 p-4 border-b border-gray-800">
            <h2 className="flex-1 font-semibold truncate">{generated.title}</h2>
            <button onClick={copyDoc} title="Copy" className="text-gray-400 hover:text-white"><Copy size={18} /></button>
            <button onClick={downloadDoc} title="Download .md" className="text-gray-400 hover:text-white"><Download size={18} /></button>
            <button onClick={() => setGenerated(null)} title="Close" className="text-gray-400 hover:text-white"><X size={18} /></button>
          </div>
          <div className="flex-1 overflow-y-auto p-6">
            <div className="prose prose-invert max-w-none">
              <ReactMarkdown>{generated.content}</ReactMarkdown>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

export default App;