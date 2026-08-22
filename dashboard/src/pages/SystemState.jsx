import React, { useEffect, useState } from 'react';
import { format } from 'date-fns';
import { getSystemState, toggleKillSwitch } from '../api';
import clsx from 'clsx';

export default function SystemState() {
  const [state, setState] = useState(null);
  const [toggling, setToggling] = useState(false);
  const [error, setError] = useState(null);

  const load = () =>
    getSystemState().then(setState).catch((e) => setError(e.message));

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleKillSwitch = async () => {
    if (!state) return;
    const newState = !state.kill_switch;
    const confirmed = window.confirm(
      newState
        ? '⚠️  ENGAGE kill switch? All agent cycles will halt immediately.'
        : '✅  DISENGAGE kill switch? Agents will resume trading next cycle.'
    );
    if (!confirmed) return;
    setToggling(true);
    try {
      await toggleKillSwitch(newState);
      await load();
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setToggling(false);
    }
  };

  if (!state) return <div className="text-dim animate-pulse">LOADING_SYSTEM_STATE...</div>;

  const killEngaged = state.kill_switch;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="mb-2">
        <h2 className="text-2xl font-bold tracking-widest text-primary">SYSTEM CONFIGURATION</h2>
        <p className="text-xs text-dim tracking-widest mt-1">Live colony state — refreshes every 5s.</p>
      </div>

      {error && (
        <div className="border border-danger bg-danger/10 text-danger text-xs font-mono p-3 tracking-widest">
          ERROR: {error}
        </div>
      )}

      {/* Kill Switch */}
      <div className={clsx(
        'border p-6 flex items-center justify-between',
        killEngaged ? 'border-danger bg-danger/10' : 'border-panel-border bg-panel'
      )}>
        <div>
          <div className={clsx(
            'text-[10px] tracking-widest uppercase mb-1',
            killEngaged ? 'text-danger' : 'text-dim'
          )}>
            KILL_SWITCH
          </div>
          <div className={clsx(
            'text-3xl font-bold tracking-widest',
            killEngaged ? 'text-danger' : 'text-alive'
          )}>
            {killEngaged ? '■ ENGAGED' : '● DISENGAGED'}
          </div>
          {killEngaged && state.kill_switch_set_at && (
            <div className="text-xs text-danger/70 mt-1 font-mono">
              Engaged at: {format(new Date(state.kill_switch_set_at), 'yyyy-MM-dd HH:mm:ss')}
              {' '}· By: {state.updated_by}
            </div>
          )}
          {!killEngaged && (
            <div className="text-xs text-dim mt-1">All agent cycles are running normally.</div>
          )}
        </div>
        <button
          onClick={handleKillSwitch}
          disabled={toggling}
          className={clsx(
            'px-6 py-3 text-sm font-bold tracking-widest uppercase border transition-colors',
            toggling && 'opacity-50 cursor-not-allowed',
            killEngaged
              ? 'border-alive text-alive hover:bg-alive/10'
              : 'border-danger text-danger hover:bg-danger/10'
          )}
        >
          {toggling ? 'PROCESSING...' : killEngaged ? 'DISENGAGE' : 'ENGAGE'}
        </button>
      </div>

      {/* Colony Stats */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="ALIVE_AGENTS" value={state.alive_agents} color="text-alive" />
        <StatCard label="DEAD_AGENTS" value={state.dead_agents} color="text-danger" />
        <StatCard
          label="TOTAL_BALANCE"
          value={`$${parseFloat(state.total_balance).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          color="text-gold"
        />
        <StatCard
          label="TOTAL_TAX_RESERVE"
          value={`$${parseFloat(state.total_tax_reserve).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          color="text-danger"
        />
      </div>

      {/* Raw state for reference */}
      <div className="border border-panel-border bg-panel">
        <div className="p-3 border-b border-panel-border text-[10px] tracking-widest text-dim uppercase">
          RAW_STATE_DUMP
        </div>
        <pre className="p-4 text-xs font-mono text-muted overflow-auto">
          {JSON.stringify(state, null, 2)}
        </pre>
      </div>
    </div>
  );
}

function StatCard({ label, value, color }) {
  return (
    <div className="border border-panel-border bg-panel p-4">
      <div className="text-[10px] tracking-widest text-dim uppercase mb-2">{label}</div>
      <div className={clsx('text-2xl font-bold', color)}>{value}</div>
    </div>
  );
}
