import React, { useRef, useState } from 'react';
import { uploadDocument } from '../api';

// onUploaded is a callback from the parent (App). After a successful upload
// we call it so App can refresh the document list.
interface Props {
  onUploaded: () => void;
}

function UploadZone({ onUploaded }: Props) {
  // Ref to the hidden <input type="file">, so clicking the box can open the picker
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);   // highlights the box on drag-over
  const [uploading, setUploading] = useState(false); // shows "Processing..." state
  const [error, setError] = useState('');

  // Upload each file one at a time. Flask extracts and embeds on every upload,
  // which can take a few seconds, so we show a loading state.
  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setError('');
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        await uploadDocument(file);
      }
      onUploaded();   // tell the parent to reload the document list
    } catch (e: any) {
      // Flask sends { error: '...' } on failure, so show that message if present
      setError(e?.response?.data?.error || 'Upload failed');
    } finally {
      setUploading(false);
    }
  }

  return (
    <div
      onClick={() => inputRef.current?.click()}
      // preventDefault is required, otherwise the browser opens the file instead
      onDragOver={e => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={e => {
        e.preventDefault();
        setDragging(false);
        handleFiles(e.dataTransfer.files);   // files dropped onto the box
      }}
      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
        dragging ? 'border-blue-400 bg-blue-500/10' : 'border-gray-700 hover:border-gray-500'
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.png,.jpg,.jpeg,.gif,.bmp,.tiff"
        className="hidden"
        onChange={e => handleFiles(e.target.files)}
      />
      {uploading ? (
        <p className="text-blue-400">Processing... extracting text and embedding</p>
      ) : (
        <>
          <p className="text-gray-300">Drop PDFs or images here</p>
          <p className="text-gray-500 text-sm mt-1">or click to browse</p>
        </>
      )}
      {error && <p className="text-red-400 text-sm mt-3">{error}</p>}
    </div>
  );
}

export default UploadZone;