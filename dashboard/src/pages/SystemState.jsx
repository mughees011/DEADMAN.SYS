import React, { useEffect, useState } from 'react';
import { getSystemState } from '../api';

export default function SystemState() {
  const [state, setState] = useState(null);

  useEffect(() => {
    getSystemState().then(setState).catch(console.error);
  }, []);

  if (!state) return <div className="text-dim">LOADING...</div>;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold tracking-widest text-primary mb-4">SYSTEM CONFIGURATION</h2>
      <pre className="bg-panel border border-panel-border p-4 text-xs font-mono text-muted overflow-auto">
        {JSON.stringify(state, null, 2)}
      </pre>
    </div>
  );
}
