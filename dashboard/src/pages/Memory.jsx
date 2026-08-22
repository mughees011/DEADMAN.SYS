import React, { useEffect, useState } from 'react';
import { format } from 'date-fns';
import { getMemory } from '../api';

export default function Memory() {
  const [lessons, setLessons] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getMemory(100);
        setLessons(data);
      } catch (err) {
        console.error('Failed to load memory', err);
      } finally {
        setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h2 className="text-2xl font-bold tracking-widest text-primary mb-2">COLLECTIVE MEMORY MODULE</h2>
        <p className="text-sm text-dim tracking-widest">
          Archived heuristic extraction &amp; terminal state analysis.
          {' '}<span className="text-muted">{lessons.length} record(s) stored.</span>
        </p>
      </div>

      <div className="border border-panel-border bg-panel">
        {/* Header */}
        <div className="grid grid-cols-12 gap-4 p-4 border-b border-panel-border text-[10px] tracking-widest text-dim uppercase">
          <div className="col-span-2">TIMESTAMP</div>
          <div className="col-span-2">SOURCE_AGENT</div>
          <div className="col-span-8">HEURISTIC_EXTRACT</div>
        </div>

        {/* Rows */}
        <div className="divide-y divide-panel-border/50">
          {loading && (
            <div className="p-8 text-center text-dim text-xs tracking-widest animate-pulse">
              LOADING_MEMORY...
            </div>
          )}

          {!loading && lessons.length === 0 && (
            <div className="p-8 text-center text-dim text-sm tracking-widest">
              <div className="mb-2">MEMORY MODULE IS CURRENTLY EMPTY.</div>
              <div className="text-xs text-muted">NO TERMINAL EVENTS LOGGED YET. AGENTS MUST DIE OR TRADE TO GENERATE LESSONS.</div>
            </div>
          )}

          {lessons.map((lesson) => {
            // Detect if it's a death event vs a trade lesson
            const isDeath = lesson.text.toLowerCase().includes('died');

            return (
              <div
                key={lesson.id}
                className="grid grid-cols-12 gap-4 p-4 items-start text-xs hover:bg-panel-border/10 transition-colors"
              >
                <div className="col-span-2 font-mono text-dim">
                  {format(new Date(lesson.created_at), 'yyyy-MM-dd')}
                  <div className="text-[10px] mt-0.5 text-muted">
                    {format(new Date(lesson.created_at), 'HH:mm:ss')}
                  </div>
                </div>

                <div className="col-span-2">
                  {lesson.source_agent_id ? (
                    <span className="font-mono text-[10px] text-muted break-all">
                      {lesson.source_agent_id.split('-')[0].toUpperCase()}
                    </span>
                  ) : (
                    <span className="text-dim">SYSTEM</span>
                  )}
                </div>

                <div className={`col-span-8 leading-relaxed ${isDeath ? 'text-danger' : 'text-primary'}`}>
                  {isDeath && (
                    <span className="inline-block text-[10px] tracking-widest border border-danger text-danger px-1.5 py-0.5 mr-2 mb-1">
                      TERMINAL
                    </span>
                  )}
                  {lesson.text}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
