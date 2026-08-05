import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Roster from './pages/Roster';
import AgentAnalytics from './pages/AgentAnalytics';
import Memory from './pages/Memory';
import SystemState from './pages/SystemState';
import Login from './pages/Login';
import { getSystemState } from './api';

function ProtectedRoute({ children }) {
  const [authStatus, setAuthStatus] = useState('checking');

  useEffect(() => {
    getSystemState()
      .then(() => setAuthStatus('authed'))
      .catch(() => setAuthStatus('unauthed'));
  }, []);

  if (authStatus === 'checking') return <div className="p-8 text-muted">AUTHORIZING...</div>;
  if (authStatus === 'unauthed') return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        
        <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route index element={<Roster />} />
          <Route path="analytics/:agentId?" element={<AgentAnalytics />} />
          <Route path="memory" element={<Memory />} />
          <Route path="system" element={<SystemState />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
