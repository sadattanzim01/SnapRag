import React from 'react';
import { X } from 'lucide-react';
import { DocumentInfo, fileUrl } from '../api';

interface Props {
  doc: DocumentInfo;
  onClose: () => void;
  // True while a divider is being dragged. An iframe swallows mouse events,
  // which would make the drag stick, so we switch pointer events off for it.
  dragging: boolean;
}

function DocViewer({ doc, onClose, dragging }: Props) {
  const url = fileUrl(doc.id);

  // No fixed width or height here anymore: the parent resizable panel decides
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-800">
        <h2 className="flex-1 font-semibold truncate text-sm" title={doc.filename}>{doc.filename}</h2>
        <button onClick={onClose} title="Close" className="text-gray-400 hover:text-white">
          <X size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-auto bg-gray-900">
        {doc.file_type === 'pdf' ? (
          <iframe
            key={doc.id}
            src={url}
            title={doc.filename}
            className={`w-full h-full border-0 ${dragging ? 'pointer-events-none' : ''}`}
          />
        ) : (
          <img key={doc.id} src={url} alt={doc.filename} className="w-full" />
        )}
      </div>
    </div>
  );
}

export default DocViewer;