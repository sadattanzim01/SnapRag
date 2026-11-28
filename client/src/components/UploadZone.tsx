import React, { useRef, useState } from 'react';
import { uploadDocument, errorMessage } from '../api';

interface Props {
  onUploaded: () => void;
}

function UploadZone({ onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  // Files upload one at a time because the server processes each one
  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setError('');
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        await uploadDocument(file);
      }
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setUploading(false);
      // Refresh even after an error, since earlier files may have saved
      onUploaded();
    }
  }

  return (
    <div
      onClick={() => inputRef.current?.click()}
      // Without preventDefault the browser opens the dropped file instead
      onDragOver={e => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={e => {
        e.preventDefault();
        setDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
      className={`border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-colors ${
        dragging ? 'border-blue-400 bg-blue-500/10' : 'border-gray-700 hover:border-gray-500'
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.png,.jpg,.jpeg,.gif,.bmp,.tiff"
        className="hidden"
        onChange={e => {
          handleFiles(e.target.files);
          // Reset so choosing the same file again still triggers onChange
          e.target.value = '';
        }}
      />
      {uploading ? (
        <p className="text-blue-400">Processing...</p>
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