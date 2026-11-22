import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { FileText } from 'lucide-react';
import { askQuestion, Source, GeneratedDoc } from '../api';

interface Message {
  role: 'user' | 'assistant';
  text: string;
  sources?: Source[];
  document?: GeneratedDoc | null;   // set when this reply created a document
}

// selectedIds: documents ticked in the sidebar (the chat's scope)
// onDocument: tells App to show a generated document in the right panel
interface Props {
  selectedIds: number[];
  onDocument: (doc: GeneratedDoc) => void;
}

// Clickable examples shown in an empty chat
const SUGGESTIONS = [
  'Summarize the selected documents',
  'Create a one-page study guide from these documents',
  'Compare the key points across these documents',
];

function Chat({ selectedIds, onDocument }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function send(text?: string) {
    const question = (text ?? input).trim();
    if (!question || loading || selectedIds.length === 0) return;

    // History is built BEFORE adding the new message, because the backend
    // appends the current question itself.
    const history = messages.slice(-6).map(m => ({ role: m.role, content: m.text }));

    setMessages(prev => [...prev, { role: 'user', text: question }]);
    setInput('');
    setLoading(true);

    try {
      const res = await askQuestion(question, selectedIds, history);
      setMessages(prev => [
        ...prev,
        { role: 'assistant', text: res.answer, sources: res.sources, document: res.document },
      ]);
      // If Claude wrote a document, open it in the right panel straight away
      if (res.document) onDocument(res.document);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', text: 'Something went wrong. Is Flask running?' }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Top bar: shows how many documents the chat can see */}
      <div className="px-6 py-3 border-b border-gray-800 text-sm text-gray-400">
        {selectedIds.length === 0
          ? 'No documents selected: tick some in the sidebar'
          : `Chatting with ${selectedIds.length} document${selectedIds.length === 1 ? '' : 's'}`}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.length === 0 && (
            <div className="text-center mt-20">
              <p className="text-gray-400 mb-4">Ask a question, or have me create a new document</p>
              <div className="flex flex-col items-center gap-2">
                {SUGGESTIONS.map(s => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="text-sm border border-gray-700 hover:border-gray-500 rounded-full px-4 py-1.5 text-gray-300"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={m.role === 'user' ? 'text-right' : 'text-left'}>
              <div
                className={`inline-block max-w-[90%] rounded-xl px-4 py-2 text-left ${
                  m.role === 'user' ? 'bg-blue-600' : 'bg-gray-800'
                }`}
              >
                {m.role === 'user' ? (
                  m.text
                ) : (
                  // ReactMarkdown turns **bold**, lists and headings into real formatting.
                  // "prose" comes from the typography plugin.
                  <div className="prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown>{m.text}</ReactMarkdown>
                  </div>
                )}
              </div>

              {/* Reopen button, in case the user closed the right panel */}
              {m.document && (
                <button
                  onClick={() => onDocument(m.document!)}
                  className="mt-2 flex items-center gap-2 text-sm bg-gray-900 border border-gray-700 hover:border-blue-500 rounded-lg px-3 py-2"
                >
                  <FileText size={16} /> {m.document.title}
                </button>
              )}

              {m.sources && m.sources.length > 0 && (
                <details className="mt-2 text-sm text-gray-400">
                  <summary className="cursor-pointer hover:text-gray-200">{m.sources.length} sources</summary>
                  <div className="mt-2 space-y-2">
                    {m.sources.map((s, j) => (
                      <div key={j} className="bg-gray-900 border border-gray-800 rounded-lg p-2">
                        <p className="text-gray-300">
                          {s.filename}
                          <span className="text-gray-500"> · match {(s.similarity * 100).toFixed(0)}%</span>
                        </p>
                        <p className="text-gray-500">{s.preview}...</p>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          ))}

          {loading && <p className="text-gray-500">Thinking...</p>}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-gray-800 p-4">
        <div className="max-w-3xl mx-auto flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && send()}
            placeholder="Ask about your documents, or ask me to create one..."
            className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 outline-none focus:border-blue-500"
          />
          <button
            onClick={() => send()}
            disabled={loading || selectedIds.length === 0}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg px-4"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

export default Chat;