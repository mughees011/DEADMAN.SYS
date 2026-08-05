import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  withCredentials: true,
});

export const getSystemState = async () => {
  const { data } = await api.get('/system/state');
  return data;
};

export const getAgents = async () => {
  const { data } = await api.get('/agents');
  return data;
};

export const getAgent = async (agentId) => {
  const { data } = await api.get(`/agents/${agentId}`);
  return data;
};

export const getAgentLogs = async (agentId, limit = 50) => {
  const { data } = await api.get(`/agents/${agentId}/logs?limit=${limit}`);
  return data;
};

export const getNotes = async () => {
  const { data } = await api.get('/notes');
  return data;
};

export const createNote = async (content) => {
  const { data } = await api.post('/notes', { content });
  return data;
};

export const login = async (password) => {
  const { data } = await api.post('/login', { username: 'boss', password });
  return data;
};

export const toggleKillSwitch = async (engaged) => {
  const { data } = await api.post('/system/kill-switch', { engaged });
  return data;
};

export default api;
