import React, { useState } from 'react';
import '../App.css';
import { apiLogin, apiRegister } from '../api';

export default function LoginRegister({ onAuth }) {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [dob, setDob] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function isValidPassword(pw) {
    return pw.length >= 8 &&
      /[A-Z]/.test(pw) &&
      /[a-z]/.test(pw) &&
      /\d/.test(pw) &&
      /[^A-Za-z0-9]/.test(pw);
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (!password) {
        setError('Password is required.');
        setLoading(false);
        return;
      }
      if (mode === 'register' && !isValidPassword(password)) {
        setError('Password must be at least 8 characters, include uppercase, lowercase, number, and special character.');
        setLoading(false);
        return;
      }
      if (mode === 'login') {
        const res = await apiLogin(email, password);
        if (res.error) setError(res.error);
        else onAuth({ email, name: res.name || '' });
      } else {
        const res = await apiRegister(email, name, dob, password);
        if (res.error) setError(res.error);
        else onAuth({ email, name });
      }
    } catch (err) {
      setError('Server error');
    }
    setLoading(false);
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2>{mode === 'login' ? 'Login' : 'Register'}</h2>
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
            autoFocus
          />
          {mode === 'register' && (
            <>
              <input
                type="text"
                placeholder="Name"
                value={name}
                onChange={e => setName(e.target.value)}
                required
              />
              <input
                type="date"
                placeholder="Date of Birth"
                value={dob}
                onChange={e => setDob(e.target.value)}
                required
              />
            </>
          )}
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />
          {error && <div className="auth-error">{error}</div>}
          <button type="submit" disabled={loading}>{loading ? 'Please wait...' : (mode === 'login' ? 'Login' : 'Register')}</button>
        </form>
        <div className="auth-switch">
          {mode === 'login' ? (
            <span>Don't have an account? <button onClick={() => setMode('register')}>Register</button></span>
          ) : (
            <span>Already registered? <button onClick={() => setMode('login')}>Login</button></span>
          )}
        </div>
      </div>
    </div>
  );
}
