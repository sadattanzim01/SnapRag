import React, { useEffect, useRef, useState } from 'react';
import { askQuestion, Source } from '../api';

// One message in the conversation. Only assistant messages carry sources.
interface Message {
  role: 'user' | 'assistant';
  text: string;
  sources?: Source[];
}

function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Scroll to the newest message whenever the list changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function send() {
    const question = input.trim();
    if (!question || loading) return;

    // Show the user's message immediately, before waiting for Flask
    setMessages(prev => [...prev, { role: 'user', text: question }]);
    setInput('');
    setLoading(true);

    try {
      const res = await askQuestion(question);
      setMessages(prev => [...prev, { role: 'assistant', text: res.answer, sources: res.sources }]);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', text: 'Something went wrong. Is Flask running?' }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-[520px] bg-gray-900 border border-gray-800 rounded-xl">
      {/* Message list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <p className="text-gray-500 text-center mt-16">Ask a question about your documents</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : 'text-left'}>
            <div className={`inline-block max-w-[85%] rounded-xl px-4 py-2 whitespace-pre-wrap text-left ${
              m.role === 'user' ? 'bg-blue-600' : 'bg-gray-800'
            }`}>
              {m.text}
            </div>

            {/* Sources: the evidence Claude used. <details> gives us expand/collapse for free */}
            {m.sources && m.sources.length > 0 && (
              <details className="mt-2 text-sm text-gray-400">
                <summary className="cursor-pointer hover:text-gray-200">
                  {m.sources.length} sources
                </summary>
                <div className="mt-2 space-y-2">
                  {m.sources.map((s, j) => (
                    <div key={j} className="bg-gray-950 border border-gray-800 rounded-lg p-2">
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

      {/* Input row. Enter sends the message */}
      <div className="border-t border-gray-800 p-3 flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="Ask about your documents..."
          className="flex-1 bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 outline-none focus:border-blue-500"
        />
        <button
          onClick={send}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg px-4"
        >
          Send
        </button>
      </div>
    </div>
  );
}

export default Chat;