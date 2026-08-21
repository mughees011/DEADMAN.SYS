import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import { getSystemState, getAgents } from '../api';

export default function Roster() {
  const [state, setState] = useState(null);
  const [agents, setAgents] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    const loadData = async () => {
      try {
        const [st, ags] = await Promise.all([getSystemState(), getAgents()]);
        setState(st);
        setAgents(ags);
      } catch (err) {
        console.error("Failed to load roster data", err);
      }
    };
    loadData();
    const interval = setInterval(loadData, 5000); // refresh every 5s
    return () => clearInterval(interval);
  }, []);

  if (!state) return <div className="p-8 text-dim animate-pulse">LOADING_DATA...</div>;

  const totalBalance = agents.reduce((sum, a) => sum + (a.alive ? parseFloat(a.balance) : 0), 0);
  const aliveCount = agents.filter(a => a.alive).length;
  const deadCount = agents.filter(a => !a.alive).length;
  
  // Calculate days left to death based on income
  const getLifespanStr = (agent) => {
    if (!agent.alive) return "0/7 DAYS";
    
    // In our backend, the agent dies if days_since_income > 7.
    // We can calculate the days passed via Python but here we just approximate 
    // or we'd ideally get `days_since_income` from backend.
    // For now we calculate it on frontend:
    const lastIncome = new Date(agent.last_income_at || agent.born_at);
    const lastEval = new Date(agent.last_evaluated_at || agent.born_at);
    const msInDay = 1000 * 60 * 60 * 24;
    const daysSince = Math.floor((lastEval - lastIncome) / msInDay);
    const remaining = Math.max(0, 7 - daysSince);
    return `${remaining}/7 DAYS`;
  };

  const getLifespanWidth = (agent) => {
    if (!agent.alive) return "0%";
    const str = getLifespanStr(agent);
    const remaining = parseInt(str.split('/')[0]);
    return `${(remaining / 7) * 100}%`;
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Top Stats */}
      <div className="grid grid-cols-4 gap-0 border border-panel-border bg-panel text-sm">
        <div className="p-4 border-r border-panel-border">
          <div className="text-[10px] tracking-widest text-dim uppercase mb-2">Tick / Day Count</div>
          <div className="text-2xl text-primary">{state.cycle_count}</div>
        </div>
        <div className="p-4 border-r border-panel-border">
          <div className="text-[10px] tracking-widest text-dim uppercase mb-2">Agents (A/D)</div>
          <div className="text-2xl text-alive font-bold">
            {aliveCount} <span className="text-dim font-normal mx-1">/</span> <span className="text-danger">{deadCount}</span>
          </div>
        </div>
        <div className="p-4 border-r border-panel-border">
          <div className="text-[10px] tracking-widest text-dim uppercase mb-2">Total Balance</div>
          <div className="text-2xl text-gold">${totalBalance.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
        </div>
        <div className="p-4">
          <div className="text-[10px] tracking-widest text-dim uppercase mb-2">Tax Reserve</div>
          <div className="text-2xl text-danger">${parseFloat(state.total_tax_reserve).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
        </div>
      </div>

      {/* Roster Table */}
      <div className="border border-panel-border bg-panel">
        <div className="grid grid-cols-12 gap-4 p-4 border-b border-panel-border text-[10px] tracking-widest text-dim uppercase">
          <div className="col-span-5">Agent ID (Gen)<br/>Status</div>
          <div className="col-span-4 text-right">Balance</div>
          <div className="col-span-3 text-right">Lifespan / Tax</div>
        </div>

        <div className="divide-y divide-panel-border/50">
          {agents.map((agent) => (
            <div 
              key={agent.id} 
              className={clsx(
                "grid grid-cols-12 gap-4 p-4 items-center cursor-pointer transition-colors hover:bg-panel-border/20",
                !agent.alive && "opacity-50"
              )}
              onClick={() => navigate(`/analytics/${agent.id}`)}
            >
              {/* Name and Status */}
              <div className="col-span-5">
                <div className="flex items-center">
                  {/* Indentation for children */}
                  {Array(agent.generation).fill(0).map((_, i) => (
                    <span key={i} className="w-6 inline-block text-dim">↳</span>
                  ))}
                  <span className="font-bold text-primary mr-2">{agent.name}</span>
                  <span className="text-[10px] px-1.5 py-0.5 bg-panel-border text-muted">G{agent.generation}</span>
                </div>
                <div className={clsx(
                  "text-[10px] tracking-widest uppercase mt-1 flex items-center",
                  agent.alive ? "text-alive" : "text-danger"
                )}>
                  {agent.alive ? 'ALIVE' : 'DEAD'} 
                  <span className="w-1.5 h-1.5 ml-2 bg-current shadow-[0_0_4px_currentColor]"></span>
                </div>
              </div>

              {/* Balance */}
              <div className={clsx(
                "col-span-4 text-right font-mono text-sm",
                agent.alive && agent.balance >= 500 ? "text-gold" : 
                agent.alive && agent.balance < 100 ? "text-warn" : 
                "text-muted"
              )}>
                ${agent.balance.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
              </div>

              {/* Lifespan */}
              <div className="col-span-3 flex flex-col items-end justify-center">
                <div className="text-xs text-muted mb-1">{getLifespanStr(agent)}</div>
                <div className="w-24 h-1 bg-panel-border">
                  <div 
                    className={clsx("h-full transition-all", agent.alive ? "bg-alive" : "bg-danger")} 
                    style={{ width: getLifespanWidth(agent) }}
                  ></div>
                </div>
                <div className="text-[10px] text-danger mt-1 font-mono">
                  Tax ${parseFloat(agent.tax_reserve).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
