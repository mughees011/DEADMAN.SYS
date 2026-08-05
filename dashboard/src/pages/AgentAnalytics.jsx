import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { LineChart, Line, ResponsiveContainer, YAxis, ReferenceLine } from 'recharts';
import clsx from 'clsx';
import { getAgent, getAgentLogs } from '../api';
import { format } from 'date-fns';

export default function AgentAnalytics() {
  const { agentId } = useParams();
  const navigate = useNavigate();
  const [agent, setAgent] = useState(null);
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    if (!agentId) return;
    const load = async () => {
      try {
        const ag = await getAgent(agentId);
        const lg = await getAgentLogs(agentId);
        setAgent(ag);
        setLogs(lg);
      } catch (err) {
        console.error("Failed to load analytics", err);
      }
    };
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [agentId]);

  if (!agentId) {
    return <div className="text-dim">SELECT AN AGENT FROM THE ROSTER TO VIEW ANALYTICS.</div>;
  }

  if (!agent) {
    return <div className="text-dim animate-pulse">LOADING_DATA...</div>;
  }

  // Construct chart data from logs (reverse to get chronological)
  const chartData = [...logs].reverse().map(l => ({
    cycle: l.cycle_count || 0,
    balance: l.agent_balance_after !== null ? l.agent_balance_after : agent.balance
  }));

  // Initial balance is seed amount or balance before first log. 
  // Let's just prepend a 0-point if we want.
  if (chartData.length > 0) {
    chartData.unshift({ cycle: chartData[0].cycle - 1, balance: chartData[0].balance - logs[logs.length-1].net_result });
  } else {
    chartData.push({ cycle: 0, balance: agent.balance });
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header Info */}
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-bold flex items-center text-primary">
            <span className="text-alive mr-3">■</span> 
            {agent.name} [G{agent.generation}]
          </h2>
          <div className="text-xs text-dim tracking-widest uppercase mt-2">
            CLASS: TRADER // STATUS: {agent.alive ? 'AUTONOMOUS' : 'TERMINATED'}
          </div>
        </div>
        
        <div className="flex gap-4">
          <div className="border border-panel-border bg-panel p-4 w-40">
            <div className="text-[10px] text-dim tracking-widest uppercase mb-1">CURRENT_BAL</div>
            <div className="text-xl text-alive">${agent.balance.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
          </div>
          <div className="border border-gold bg-panel p-4 w-40">
            <div className="text-[10px] text-gold tracking-widest uppercase mb-1">DEAD_MAN_SWITCH</div>
            <div className="text-xl text-primary">
              {agent.alive ? '7/7 DAYS' : '0/7 DAYS'}
            </div>
          </div>
        </div>
      </div>

      {/* Chart & Side Panels */}
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 border border-panel-border bg-panel p-4 relative h-64">
          <div className="flex justify-between text-[10px] tracking-widest text-dim uppercase mb-4">
            <span>BALANCE_TRAJECTORY_T-7</span>
          </div>
          
          <div className="absolute inset-x-4 top-12 bottom-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <YAxis domain={['auto', 'auto']} hide />
                <ReferenceLine y={0} stroke="var(--color-dim)" strokeDasharray="3 3" />
                <Line 
                  type="stepAfter" 
                  dataKey="balance" 
                  stroke="var(--color-alive)" 
                  strokeWidth={3} 
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="col-span-1 space-y-6">
          <div className="border border-panel-border bg-panel p-4 h-full">
            <div className="text-[10px] text-dim tracking-widest uppercase mb-2">LAST_HEARTBEAT</div>
            <div className="text-sm text-primary flex items-center">
              <span className="text-alive mr-2">♡</span> 
              TICK_{logs[0]?.cycle_count || '?'}
            </div>
          </div>
        </div>
      </div>

      {/* Decision Log Timeline */}
      <div className="border border-panel-border bg-panel">
        <div className="flex justify-between p-4 border-b border-panel-border text-[10px] tracking-widest text-dim uppercase">
          <span>DECISION_LOG_TIMELINE</span>
          <button className="hover:text-primary transition-colors">EXPORT_CSV</button>
        </div>
        
        <div className="grid grid-cols-12 gap-4 p-4 border-b border-panel-border text-[10px] tracking-widest text-dim uppercase">
          <div className="col-span-2">TIMESTAMP</div>
          <div className="col-span-3">SITUATION_SNAPSHOT</div>
          <div className="col-span-3">ACTION_TAKEN</div>
          <div className="col-span-3">LEGALITY_JUSTIFICATION</div>
          <div className="col-span-1 text-right">RESULT</div>
        </div>

        <div className="divide-y divide-panel-border/50">
          {logs.map((log) => (
            <div 
              key={log.id}
              className={clsx(
                "grid grid-cols-12 gap-4 p-4 text-xs items-start",
                log.error ? "text-danger bg-danger/5" : "text-primary"
              )}
            >
              <div className="col-span-2 font-mono text-dim">
                {format(new Date(log.cycle_at), 'yyyy-MM-dd HH:mm:ss')}
              </div>
              <div className="col-span-3 text-muted pr-4 truncate" title={log.plan_text}>
                {log.error ? "SYSTEM_ERROR" : log.plan_text}
              </div>
              <div className={clsx(
                "col-span-3 font-mono",
                log.chosen_channel === 'WAIT' ? 'text-dim' : 'text-gold'
              )}>
                {log.error ? "CRASH" : log.chosen_channel || 'WAIT'}
              </div>
              <div className="col-span-3 text-muted pr-4 truncate" title={log.legality_justification}>
                {log.legality_justification || '--'}
              </div>
              <div className={clsx(
                "col-span-1 text-right font-mono",
                parseFloat(log.net_result) > 0 ? "text-alive" : parseFloat(log.net_result) < 0 ? "text-danger" : "text-dim"
              )}>
                {(() => {
                const net = parseFloat(log.net_result) || 0;
                return net > 0 ? `+$${net.toFixed(2)}` :
                       net < 0 ? `-$${Math.abs(net).toFixed(2)}` : '--';
              })()}
              </div>
            </div>
          ))}
          {logs.length === 0 && (
            <div className="p-8 text-center text-dim text-xs tracking-widest">NO LOGS FOUND</div>
          )}
        </div>
      </div>
    </div>
  );
}
