import React, { useEffect, useRef, useState } from 'react';
//import ReactMarkdown from 'react-markdown';
import GeneratedPdf from './components/GeneratedPdf';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
//import { Copy, Download, FileText, X } from 'lucide-react';
import { getDocuments, deleteDocument, DocumentInfo, GeneratedDoc } from './api';
import UploadZone from './components/UploadZone';
import Chat from './components/Chat';
import DocViewer from './components/DocViewer';
import { FileText, X } from 'lucide-react';

const handleStyle = 'bg-gray-800 hover:bg-blue-500 data-[resize-handle-state=drag]:bg-blue-500 transition-colors';

function ColHandle({ onDragging }: { onDragging: (d: boolean) => void }) {
  return <PanelResizeHandle onDragging={onDragging} className={`w-1.5 ${handleStyle}`} />;
}

function RowHandle({ onDragging }: { onDragging: (d: boolean) => void }) {
  return <PanelResizeHandle onDragging={onDragging} className={`h-1.5 ${handleStyle}`} />;
}

function App() {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [generated, setGenerated] = useState<GeneratedDoc | null>(null);
  const [viewingId, setViewingId] = useState<number | null>(null);
  const [dragging, setDragging] = useState(false);

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
    if (viewingId === id) setViewingId(null);
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

  const viewing = docs.find(d => d.id === viewingId) || null;

  // function copyDoc() {
  //   if (generated) navigator.clipboard.writeText(generated.content);
  // }

  // function downloadDoc() {
  //   if (!generated) return;
  //   const blob = new Blob([generated.content], { type: 'text/markdown' });
  //   const url = URL.createObjectURL(blob);
  //   const a = document.createElement('a');
  //   a.href = url;
  //   a.download = `${generated.title}.md`;
  //   a.click();
  //   URL.revokeObjectURL(url);
  // }

  return (
    <div className="h-screen bg-gray-950 text-white">
      {/* v2 key: forgets the old saved layout so the new sizes take effect */}
      <PanelGroup direction="horizontal" autoSaveId="snaprag-layout-v2">

        {/* ── LEFT COLUMN: small by default (16%) ─────────────────────────── */}
        <Panel id="left" order={1} defaultSize={16} minSize={10}>
          <PanelGroup direction="vertical">

            <Panel id="doclist" order={1} defaultSize={50} minSize={20}>
              <div className="h-full overflow-y-auto">
                <div className="p-4 border-b border-gray-800">
                  {/* Logo + name side by side. Files in /public are served from the site root, so "/logo.png" works */}
                  <div className="flex items-center gap-2">
                    <img src="/logo.png" alt="SnapRAG" className="w-8 h-8 rounded-lg shrink-0" />
                    <h1 className="text-xl font-bold truncate">SnapRAG</h1>
                  </div>
                </div>  

                <div className="p-3">
                  <UploadZone onUploaded={loadDocs} />
                </div>

                <div className="px-3 flex items-center justify-between text-xs text-gray-400">
                  <span>{selected.size} of {docs.length} selected</span>
                  <button onClick={toggleAll} className="hover:text-white">
                    {allSelected ? 'None' : 'All'}
                  </button>
                </div>

                <div className="p-3 space-y-2">
                  {docs.map(d => (
                    <div
                      key={d.id}
                      className={`flex items-center gap-2 border rounded-lg px-2 py-2 ${
                        viewingId === d.id ? 'bg-gray-800 border-blue-500' : 'bg-gray-900 border-gray-800'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selected.has(d.id)}
                        onChange={() => toggle(d.id)}
                        className="accent-blue-500"
                      />
                      <button
                        onClick={() => setViewingId(d.id)}
                        className="flex flex-1 items-center gap-2 min-w-0 text-left hover:text-blue-400"
                        title={`Open ${d.filename}`}
                      >
                        <FileText size={14} className="text-gray-500 shrink-0" />
                        <span className="truncate text-xs">{d.filename}</span>
                      </button>
                      <button onClick={() => handleDelete(d.id)} className="text-gray-500 hover:text-red-400">
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                  {docs.length === 0 && <p className="text-gray-500 text-xs">No documents yet.</p>}
                </div>
              </div>
            </Panel>

            {viewing && (
              <>
                <RowHandle onDragging={setDragging} />
                <Panel id="viewer" order={2} defaultSize={50} minSize={20}>
                  <DocViewer doc={viewing} onClose={() => setViewingId(null)} dragging={dragging} />
                </Panel>
              </>
            )}
          </PanelGroup>
        </Panel>

        <ColHandle onDragging={setDragging} />

        {/* ── MIDDLE: chat. No defaultSize, so it fills all remaining space ── */}
        <Panel id="chat" order={2} minSize={30}>
          <div className="h-full">
            <Chat selectedIds={Array.from(selected)} onDocument={setGenerated} />
          </div>
        </Panel>

        {/* ── RIGHT: only exists when Claude generated a document ─────────── */}
        {/* ── RIGHT: generated document shown as a PDF ── */}
        {generated && (
          <>
            <ColHandle onDragging={setDragging} />
            <Panel id="generated" order={3} defaultSize={34} minSize={15}>
              <GeneratedPdf generated={generated} onClose={() => setGenerated(null)} dragging={dragging} />
            </Panel>
          </>
        )}
      </PanelGroup>
    </div>
  );
}

export default App;