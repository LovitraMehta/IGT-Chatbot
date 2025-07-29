import { useState, useRef, useEffect, useCallback } from 'react';
import MessageBubble from './MessageBubble';
import { sendMessage, uploadFiles, getChatHistory, getUploadedFiles, startNewChat, getChatsHistory, getChatByIndex } from '../api';

export default function Chatbot({ user, freshChat, chatIdx, initialMessages }) {
  const [messages, setMessages] = useState(() => {
    if (initialMessages && initialMessages.length > 0) {
      return initialMessages;
    }
    return [
      { role: 'assistant', content: `Hello ${user.name}, how can I help you today?` }
    ];
  });
  const [input, setInput] = useState('');
  const [files, setFiles] = useState([]);
  const [contextMode, setContextMode] = useState('global');
  const [selectedDoc, setSelectedDoc] = useState('');
  const [selectedDocs, setSelectedDocs] = useState([]);
  const [showContextPanel, setShowContextPanel] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const chatEndRef = useRef(null);

  // Memoized fetchUploadedFiles to avoid React Hook warning
  const fetchUploadedFiles = useCallback(async () => {
    const files = await getUploadedFiles();
    setUploadedFiles(files);
    // Set default selectedDoc if needed
    if (files.length > 0 && !selectedDoc) {
      setSelectedDoc(files[0]);
    }
  }, [selectedDoc]);

  // Load chat session if chatIdx is set, else new chat
  useEffect(() => {
    async function loadChat() {
      if (chatIdx !== null && chatIdx !== undefined) {
        const data = await getChatByIndex(chatIdx);
        if (data && data.history) {
          setMessages(data.history);
        } else {
          setMessages([{ role: 'assistant', content: `Hello ${user.name}, how can I help you today?` }]);
        }
      } else {
        setMessages([{ role: 'assistant', content: `Hello ${user.name}, how can I help you today?` }]);
      }
    }
    loadChat();
    setInput('');
    setFiles([]);
    setContextMode('global');
    setSelectedDoc('');
    setSelectedDocs([]);
    setShowContextPanel(false);
    setUploadedFiles([]);
    fetchUploadedFiles();
    // eslint-disable-next-line
  }, [freshChat, user.name, chatIdx]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    setMessages([...messages, { role: 'user', content: input }]);
    setInput('');
    const payload = {
      question: input,
      context_mode: contextMode,
      selected_doc: contextMode === 'document' ? selectedDoc : undefined,
      selected_docs: contextMode === 'custom' ? selectedDocs : undefined,
    };
    const res = await sendMessage(payload);
    setMessages(msgs => [...msgs, { role: 'assistant', content: res.answer, answer_html: res.answer_html }]);
  };

  const handleFileChange = (e) => {
    setFiles(e.target.files);
  };

  const handleUpload = async () => {
    if (!files || files.length === 0) return;
    await uploadFiles(files);
    alert('Files uploaded!');
    fetchUploadedFiles();
  };

  // UI for context selection in a side panel
  const renderContextPanel = () => (
    <div className="context-panel" style={{ display: showContextPanel ? 'block' : 'none' }}>
      <div className="context-panel-header">
        <h4>Context Selection</h4>
        <button className="close-btn" onClick={() => setShowContextPanel(false)}>
          <span className="btn-icon">✕</span>
        </button>
      </div>
      <div className="context-options">
        <label className="radio-option">
          <input type="radio" name="context_mode" value="global" checked={contextMode === 'global'} onChange={() => setContextMode('global')} />
          <span className="radio-label">Global Context</span>
        </label>
        <label className="radio-option">
          <input type="radio" name="context_mode" value="document" checked={contextMode === 'document'} onChange={() => setContextMode('document')} />
          <span className="radio-label">Single Document</span>
        </label>
        <label className="radio-option">
          <input type="radio" name="context_mode" value="custom" checked={contextMode === 'custom'} onChange={() => setContextMode('custom')} />
          <span className="radio-label">Custom Selection</span>
        </label>
      </div>
      {contextMode === 'document' && (
        <div className="document-selector">
          <label className="select-label">Select document:</label>
          <select value={selectedDoc} onChange={e => setSelectedDoc(e.target.value)} className="document-select">
            <option value="">Choose a document</option>
            {uploadedFiles.map(f => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        </div>
      )}
      {contextMode === 'custom' && (
        <div className="custom-selector">
          <label className="select-label">Select documents:</label>
          <div className="checkbox-list">
            {uploadedFiles.map(f => (
              <label key={f} className="checkbox-option">
                <input
                  type="checkbox"
                  value={f}
                  checked={selectedDocs.includes(f)}
                  onChange={e => {
                    if (e.target.checked) setSelectedDocs([...selectedDocs, f]);
                    else setSelectedDocs(selectedDocs.filter(x => x !== f));
                  }}
                />
                <span className="checkbox-label">{f}</span>
              </label>
            ))}
          </div>
          <small className="help-text">You can select any number of documents.</small>
        </div>
      )}
    </div>
  );

  return (
    <div className="chatbot-container">
      <div className="chat-window">
        {messages.map((msg, idx) => (
          <MessageBubble key={idx} message={msg} />
        ))}
        <div ref={chatEndRef} />
      </div>
      {renderContextPanel()}
      <form className="chat-input-row" onSubmit={handleSend}>
        <input
          type="text"
          placeholder="Type your message..."
          value={input}
          onChange={e=>setInput(e.target.value)}
          className="chat-input"
        />
        <button type="button" className="context-btn" title="Context Options" onClick={() => setShowContextPanel(v => !v)}>
          <span className="btn-icon">⚙️</span>
        </button>
        <button type="submit" className="send-btn">
          <span className="btn-icon">📤</span>
          Send
        </button>
      </form>
      <div className="file-upload-row">
        <div className="file-input-container">
          <input type="file" multiple onChange={handleFileChange} className="file-input" />
          <label className="file-input-label">
            <span className="btn-icon">📁</span>
            Choose Files
          </label>
        </div>
        <button onClick={handleUpload} className="upload-btn">
          <span className="btn-icon">📤</span>
          Upload Files
        </button>
      </div>
    </div>
  );
}