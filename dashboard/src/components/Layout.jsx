import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { LayoutDashboard, BarChart2, History, Settings, LogOut, Power } from 'lucide-react';
import clsx from 'clsx';
import { toggleKillSwitch } from '../api';

export default function Layout() {
  const [killModalOpen, setKillModalOpen] = useState(false);
  const navigate = useNavigate();

  const navItems = [
    { name: 'ROSTER', path: '/', icon: LayoutDashboard },
    { name: 'ANALYTICS', path: '/analytics', icon: BarChart2 },
    { name: 'MEMORY', path: '/memory', icon: History },
    { name: 'SYSTEM', path: '/system', icon: Settings },
  ];

  return (
    <div className="flex h-screen w-full bg-base text-primary overflow-hidden">
      {/* Sidebar */}
      <div className="w-48 border-r border-panel-border flex flex-col bg-panel">
        <div className="p-4">
          <h1 className="text-lg font-bold tracking-wider mb-2">OPERATOR_01</h1>
          <div className="flex items-center text-[10px] tracking-widest text-alive uppercase">
            <span className="w-1.5 h-1.5 rounded-full bg-alive animate-pulse mr-2"></span>
            Status: Active
          </div>
        </div>

        <nav className="flex-1 mt-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) =>
                clsx(
                  'flex items-center px-4 py-2 text-xs font-semibold tracking-widest transition-colors',
                  isActive 
                    ? 'bg-alive text-base'
                    : 'text-muted hover:text-primary hover:bg-panel-border/30'
                )
              }
            >
              <item.icon className="w-3 h-3 mr-3" />
              {item.name}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-panel-border space-y-4">
          <button 
            onClick={() => setKillModalOpen(true)}
            className="w-full py-1.5 border border-danger text-danger hover:bg-danger/10 text-[10px] tracking-widest uppercase transition-colors flex items-center justify-center"
          >
            TERMINATE_ALL
          </button>
          <button 
            onClick={() => {
              document.cookie = "session=; Max-Age=0; path=/;";
              navigate('/login');
            }}
            className="flex items-center text-muted hover:text-primary text-[10px] tracking-widest uppercase transition-colors"
          >
            <LogOut className="w-3 h-3 mr-2" />
            Logout
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-panel-border flex items-center justify-between px-8 shrink-0">
          <div className="text-alive font-bold tracking-widest text-lg">SURVIVAL_OS_v1.0</div>
          
          <button 
            onClick={() => setKillModalOpen(true)}
            className="px-4 py-1.5 border border-danger text-danger text-xs tracking-widest uppercase hover:bg-danger hover:text-base transition-colors"
          >
            KILL SWITCH
          </button>
        </header>

        <main className="flex-1 overflow-auto p-8 relative">
          <Outlet />
        </main>
      </div>

      {/* Kill Switch Modal */}
      {killModalOpen && (
        <div className="fixed inset-0 bg-base/95 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-lg border border-danger bg-panel shadow-2xl">
            <div className="flex items-center justify-between px-4 py-2 border-b border-panel-border">
              <div className="flex items-center text-danger text-xs tracking-widest uppercase">
                <Power className="w-3 h-3 mr-2" />
                System Override Protocol
              </div>
              <div className="text-muted text-xs tracking-widest uppercase">AUTH_REQ: ROOT</div>
            </div>

            <div className="p-8 text-center flex flex-col items-center">
              <Power className="w-16 h-16 text-danger mb-6" />
              <h2 className="text-2xl font-bold tracking-widest mb-8">ENGAGE KILL SWITCH?</h2>
              
              <div className="bg-base border border-panel-border p-4 w-full text-danger text-sm tracking-widest leading-relaxed mb-8">
                EVERY AGENT STOPS IMMEDIATELY.<br/>
                NONE OF THEM CAN BE RESTARTED UNTIL YOU TURN THIS OFF.
              </div>

              <button 
                onClick={async () => {
                  await toggleKillSwitch(true);
                  setKillModalOpen(false);
                  window.location.reload();
                }}
                className="w-full py-4 border-2 border-danger text-danger text-lg tracking-widest font-bold hover:bg-danger hover:text-base transition-colors mb-4"
              >
                [ENGAGE KILL SWITCH]
              </button>
              
              <button 
                onClick={() => setKillModalOpen(false)}
                className="text-muted text-sm tracking-widest hover:text-primary transition-colors"
              >
                [CANCEL]
              </button>
            </div>
            
            <div className="flex justify-between px-4 py-2 border-t border-panel-border text-[10px] text-dim tracking-widest uppercase">
              <span>SECURE CONNECTION</span>
              <span>LATENCY: 12ms</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
