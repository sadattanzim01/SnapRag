import React from 'react';
import { X } from 'lucide-react';
import { DocumentInfo, fileUrl } from '../api';

interface Props {
  doc: DocumentInfo;
  onClose: () => void;
}

function DocViewer({ doc, onClose }: Props) {
  const url = fileUrl(doc.id);

  return (
    <section className="w-[30rem] shrink-0 border-l border-gray-800 flex flex-col">
      <div className="flex items-center gap-2 p-4 border-b border-gray-800">
        <h2 className="flex-1 font-semibold truncate" title={doc.filename}>{doc.filename}</h2>
        <button onClick={onClose} title="Close" className="text-gray-400 hover:text-white">
          <X size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-auto bg-gray-900">
        {doc.file_type === 'pdf' ? (
          // Chrome, Safari and Firefox all render PDFs inside an iframe.
          // key={doc.id} makes React load a fresh frame when you switch files.
          <iframe key={doc.id} src={url} title={doc.filename} className="w-full h-full border-0" />
        ) : (
          <img key={doc.id} src={url} alt={doc.filename} className="w-full" />
        )}
      </div>
    </section>
  );
}

export default DocViewer;