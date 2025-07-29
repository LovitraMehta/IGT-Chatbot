import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Chatbot from './components/Chatbot';
import LoginRegister from './components/LoginRegister';
import './App.css';
import { startNewChat, getChatsHistory, getChatByIndex, getChatHistory } from './api';

function App() {
  // Initialize user from localStorage if present
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [recentChats, setRecentChats] = useState([]); // Will hold chat session metadata
  const [chatKey, setChatKey] = useState(0); // For forcing Chatbot remount
  const [activeChatIdx, setActiveChatIdx] = useState(null); // null = new chat, else index in recentChats
  const [loadingChats, setLoadingChats] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [initialMessages, setInitialMessages] = useState([]);

  // Persist user to localStorage on login
  const handleAuth = async (userObj) => {
    setUser(userObj);
    localStorage.setItem('user', JSON.stringify(userObj));
    // Fetch latest chat history after login
    const history = await getChatHistory();
    setInitialMessages(history.length > 0 ? history : []);
  };

  // Clear user from localStorage on logout
  const handleLogout = async () => {
    setUser(null);
    localStorage.removeItem('user');
    setInitialMessages([]);
    // Optionally call backend logout endpoint
    await fetch('/api/logout', { method: 'POST', credentials: 'include' });
    setChatKey(prev => prev + 1); // Remount Chatbot
  };

  if (!user) {
    return <LoginRegister onAuth={handleAuth} />;
  }

  // Handler for New Chat
  const handleNewChat = async () => {
    await startNewChat();
    setChatKey(prev => prev + 1); // Remount Chatbot
    setActiveChatIdx(null);
    setDropdownOpen(false);
  };

  // Handler for Recent Chats dropdown
  const handleRecentChatsDropdown = async () => {
    setDropdownOpen(v => !v);
    if (!dropdownOpen && recentChats.length === 0) {
      setLoadingChats(true);
      const chats = await getChatsHistory();
      setRecentChats(chats);
      setLoadingChats(false);
    }
  };

  // Handler to continue a specific chat session
  const handleContinueChat = async (idx) => {
    setLoadingChats(true);
    setActiveChatIdx(idx);
    setChatKey(prev => prev + 1); // Remount Chatbot with new key
    setDropdownOpen(false);
    setLoadingChats(false);
  };

  // Provide a prop to Chatbot to indicate which chat to load (null = new, else index)
  return (
    <Router>
      <div className="main-layout">
        <aside className={`sidebar${sidebarOpen ? '' : ' collapsed'}`}> 
          <div className="sidebar-menu">
            <button className="menu-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>
              <span className="menu-icon">☰</span>
            </button>
            {sidebarOpen && (
              <nav className="nav-links">
                <button className="nav-btn primary-btn" onClick={handleNewChat}>
                  <span className="btn-icon">➕</span>
                  New Chat
                </button>
                <div className="dropdown-container">
                  <button className="nav-btn secondary-btn" onClick={handleRecentChatsDropdown}>
                    <span className="btn-icon">📋</span>
                    Recent Chats
                    <span className="dropdown-arrow">{dropdownOpen ? '▲' : '▼'}</span>
                  </button>
                  {dropdownOpen && (
                    <div className="dropdown-menu">
                      {loadingChats ? (
                        <div className="dropdown-item loading">Loading...</div>
                      ) : (
                        recentChats.length === 0 ? (
                          <div className="dropdown-item empty">No previous chats</div>
                        ) : (
                          <ul className="chat-list">
                            {recentChats.map((chat, idx) => (
                              <li key={idx} className="dropdown-item chat-item" onClick={() => handleContinueChat(idx)}>
                                <div className="chat-title">{chat.first ? chat.first.slice(0, 40) : 'Untitled Chat'}</div>
                                <div className="chat-date">{chat.started_at ? new Date(chat.started_at).toLocaleString() : ''}</div>
                              </li>
                            ))}
                          </ul>
                        )
                      )}
                    </div>
                  )}
                </div>
              </nav>
            )}
          </div>
          {sidebarOpen && (
            <div className="user-card">
              <span className="welcome">Welcome back,</span>
              <span className="username">{user.name}</span>
              <button className="logout-btn" onClick={handleLogout}>
                <span className="btn-icon">🚪</span>
                Logout
              </button>
            </div>
          )}
        </aside>
        <div className="content-area">
          <header className="topbar">
            <span className="app-title">Document Q&A Chatbot</span>
          </header>
          <Routes>
            <Route path="/chat" element={<Chatbot key={chatKey} user={user} freshChat={chatKey} chatIdx={activeChatIdx} initialMessages={initialMessages} />} />
            <Route path="*" element={<Navigate to="/chat" />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
