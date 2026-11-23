import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import html2pdf from 'html2pdf.js';
import { Download, X } from 'lucide-react';
import { GeneratedDoc } from '../api';

interface Props {
  generated: GeneratedDoc;
  onClose: () => void;
  dragging: boolean; // true while a panel handle is being dragged
}

// Claude adds citations like [Source 1, Source 6]. They are useful in chat
// but should not appear in a finished document, so we strip them for the PDF.
function stripCitations(text: string) {
  return text.replace(/\s*\[Sources?[^\]]*\]/g, '');
}

function GeneratedPdf({ generated, onClose, dragging }: Props) {
  // Hidden, light-themed copy of the document that gets turned into the PDF
  const printRef = useRef<HTMLDivElement>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);

  const options = {
    margin: 12,                                   // mm around the page
    filename: `${generated.title}.pdf`,
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: 2 },                    // higher scale = sharper text
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
    pagebreak: { mode: ['css', 'legacy'] },
  };

  // Rebuild the PDF whenever a new document arrives
  useEffect(() => {
    let cancelled = false;
    let createdUrl: string | null = null;
    setBusy(true);

    // Small delay so the hidden div has rendered before we capture it
    const timer = setTimeout(async () => {
      if (!printRef.current) return;
      try {
        const blob: Blob = await html2pdf()
          .set(options)
          .from(printRef.current)
          .outputPdf('blob');
        if (cancelled) return;
        createdUrl = URL.createObjectURL(blob);
        setPdfUrl(createdUrl);
      } finally {
        if (!cancelled) setBusy(false);
      }
    }, 300);

    return () => {
      cancelled = true;
      clearTimeout(timer);
      if (createdUrl) URL.revokeObjectURL(createdUrl); // free memory
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generated]);

  function downloadPdf() {
    if (!pdfUrl) return;
    const a = document.createElement('a');
    a.href = pdfUrl;
    a.download = `${generated.title}.pdf`;
    a.click();
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 p-4 border-b border-gray-800">
        <h2 className="flex-1 font-semibold truncate">{generated.title}</h2>
        <button onClick={downloadPdf} disabled={!pdfUrl} title="Download PDF"
          className="text-gray-400 hover:text-white disabled:opacity-40">
          <Download size={18} />
        </button>
        <button onClick={onClose} title="Close" className="text-gray-400 hover:text-white">
          <X size={18} />
        </button>
      </div>

      <div className="flex-1 min-h-0 bg-gray-900">
        {busy && <p className="p-6 text-sm text-gray-400">Creating PDF...</p>}
        {pdfUrl && (
          <iframe
            src={pdfUrl}
            title={generated.title}
            className="w-full h-full border-0"
            // while dragging a panel handle, the iframe would swallow the mouse
            style={{ pointerEvents: dragging ? 'none' : 'auto' }}
          />
        )}
      </div>

      {/* Off-screen white page: this is what gets captured into the PDF */}
      <div style={{ position: 'fixed', left: '-10000px', top: 0 }}>
        <div
          ref={printRef}
          className="prose max-w-none"
          style={{ width: '700px', background: '#fff', color: '#111', padding: '8px' }}
        >
          <ReactMarkdown>{stripCitations(generated.content)}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}

export default GeneratedPdf;