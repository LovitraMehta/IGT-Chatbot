import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { loginUser } from '../api';

export default function Login() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    const res = await loginUser(email);
    if (res.success) {
      navigate('/chat');
    } else {
      setError(res.error || 'Login failed');
    }
  };

  return (
    <div className="centered-container">
      <h2>Login</h2>
      <form onSubmit={handleSubmit} className="auth-form">
        <input type="email" placeholder="Email" value={email} onChange={e=>setEmail(e.target.value)} required />
        <button type="submit">Login</button>
        {error && <div className="error">{error}</div>}
      </form>
    </div>
  );
}
