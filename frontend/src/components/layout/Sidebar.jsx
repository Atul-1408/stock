import React from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  BarChart3,
  PieChart,
  Bot,
  Bell,
  MessageSquare,
  Trophy,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Radio,
  LogOut,
} from "lucide-react";

const NAV_GROUPS = [
  {
    title: "DESK",
    items: [
      { id: "dashboard", label: "Overview", path: "/dashboard", icon: LayoutDashboard },
      { id: "market", label: "Trade Desk", path: "/market", icon: BarChart3, badge: "PRO" },
      { id: "analytics", label: "Portfolio & Risk", path: "/analytics", icon: PieChart },
    ],
  },
  {
    title: "ALGO & SIGNALS",
    items: [
      { id: "bot", label: "Autonomous Bot", path: "/bot", icon: Bot, badge: "AI" },
      { id: "alerts", label: "Signals & Alerts", path: "/alerts", icon: Bell },
    ],
  },
  {
    title: "INTELLIGENCE",
    items: [
      { id: "chat", label: "Neural Assistant", path: "/chat", icon: MessageSquare },
      { id: "leaderboard", label: "Elite Network", path: "/leaderboard", icon: Trophy },
    ],
  },
];

export default function Sidebar({ isCollapsed, setIsCollapsed, isMobileOpen, setIsMobileOpen }) {
  const location = useLocation();

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user_id");
    window.location.href = "/login";
  };

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isMobileOpen && (
        <div
          onClick={() => setIsMobileOpen(false)}
          className="fixed inset-0 top-8 bg-black/70 backdrop-blur-sm z-30 lg:hidden"
        />
      )}

      {/* Sidebar Container */}
      <aside
        style={{ top: "32px", height: "calc(100vh - 32px)" }}
        className={`fixed top-8 bottom-0 left-0 z-40 flex flex-col bg-[#070b12] border-r border-white/10 transition-all duration-200 select-none
          ${isCollapsed ? "w-[68px]" : "w-[240px]"}
          ${isMobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
        `}
      >
        {/* Sidebar Header / Branding */}
        <div className="h-14 flex items-center justify-between px-4 border-b border-white/10 bg-[#090e17] overflow-hidden flex-shrink-0">
          <Link
            to="/dashboard"
            onClick={() => setIsMobileOpen(false)}
            className="flex items-center gap-2.5 overflow-hidden"
          >
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center flex-shrink-0">
              <span className="w-2.5 h-2.5 bg-emerald-400 rounded-sm animate-pulse" />
            </div>
            {!isCollapsed && (
              <div className="min-w-0">
                <span className="font-mono text-xs font-black tracking-widest text-white uppercase block truncate">
                  SOVEREIGN
                </span>
                <span className="text-[10px] font-mono text-cyan-400 font-semibold tracking-wider block">
                  TERMINAL v2.4
                </span>
              </div>
            )}
          </Link>

          {/* Desktop Collapse Toggle */}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            aria-label={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
            className="hidden lg:flex p-1 rounded-md text-slate-400 hover:text-white hover:bg-white/5 focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:outline-none transition-colors"
            title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>

        {/* Navigation Sections */}
        <div className="flex-1 py-4 px-2 space-y-6 overflow-y-auto overflow-x-hidden custom-scrollbar">
          {NAV_GROUPS.map((group) => (
            <div key={group.title} className="space-y-1">
              {!isCollapsed && (
                <div className="px-3 pb-1 text-[10px] font-mono font-bold tracking-widest text-slate-500 uppercase">
                  {group.title}
                </div>
              )}
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.id}
                    to={item.path}
                    onClick={() => setIsMobileOpen(false)}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all group relative
                      ${
                        isActive
                          ? "bg-white/10 text-white font-semibold"
                          : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                      }
                      ${isCollapsed ? "justify-center px-0" : ""}
                    `}
                    title={isCollapsed ? item.label : undefined}
                  >
                    {/* Active Route Indicator Bar */}
                    {isActive && (
                      <span className="absolute left-0 top-1.5 bottom-1.5 w-1 bg-emerald-400 rounded-r-full" />
                    )}

                    <Icon
                      size={17}
                      className={isActive ? "text-emerald-400" : "text-slate-400 group-hover:text-slate-200"}
                    />

                    {!isCollapsed && (
                      <span className="flex-1 truncate">{item.label}</span>
                    )}

                    {!isCollapsed && item.badge && (
                      <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </div>

        {/* Sidebar Footer / System Status */}
        <div className="p-3 border-t border-white/10 bg-[#080d16] space-y-2">
          {!isCollapsed ? (
            <div className="px-2 py-1.5 rounded-md bg-white/5 border border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-ping" />
                <span className="text-[10px] font-mono text-slate-300 font-semibold tracking-wide">
                  FEED: LIVE
                </span>
              </div>
              <span className="text-[9px] font-mono text-emerald-400 bg-emerald-500/10 px-1 rounded">
                WAL OK
              </span>
            </div>
          ) : (
            <div className="flex justify-center" title="Feed: Live | WAL Mode">
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
            </div>
          )}

          <button
            onClick={handleLogout}
            className={`w-full flex items-center gap-2 px-3 py-2 text-xs font-semibold text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors
              ${isCollapsed ? "justify-center px-0" : ""}
            `}
            title={isCollapsed ? "Sign Out" : undefined}
          >
            <LogOut size={16} />
            {!isCollapsed && <span>Disconnect</span>}
          </button>
        </div>
      </aside>
    </>
  );
}
