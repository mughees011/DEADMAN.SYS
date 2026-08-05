import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../api';

export default function Login() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      await login(password);
      navigate('/');
    } catch (err) {
      setError('ACCESS DENIED: Invalid credentials.');
    }
  };

  return (
    <div className="min-h-screen bg-base text-primary flex items-center justify-center p-4">
      <div className="w-full max-w-md border border-panel-border bg-panel p-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold tracking-widest text-alive">DEADMAN.SYS</h1>
          <p className="text-xs tracking-widest text-muted mt-2">SURVIVAL AGENT DASHBOARD v1.0</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          <div>
            <label className="block text-xs font-semibold tracking-widest text-dim uppercase mb-2">
              Boss Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-base border border-panel-border p-3 text-primary focus:outline-none focus:border-alive transition-colors font-mono"
              placeholder="Enter password..."
              autoFocus
            />
          </div>

          {error && (
            <div className="text-xs text-danger tracking-widest">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="w-full py-3 bg-panel-border hover:bg-alive hover:text-base border border-panel-border text-sm font-bold tracking-widest transition-colors uppercase"
          >
            Authenticate
          </button>
        </form>
      </div>
    </div>
  );
}
