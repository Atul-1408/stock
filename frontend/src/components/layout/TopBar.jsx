import React, { useState, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Menu,
  Bell,
  HelpCircle,
  ChevronDown,
  User,
  LogOut,
  Wallet,
  Search,
  ShieldCheck,
  ShieldAlert,
  Moon,
  Sun,
} from "lucide-react";
import api from "../../utils/api";
import CurrencySelector from "../CurrencySelector";
import { useCurrency } from "../../contexts/CurrencyContext";
import { formatCurrency } from "../../utils/currency";

const ROUTE_LABELS = {
  "/dashboard": { desk: "DESK", label: "MARKET OVERVIEW" },
  "/market": { desk: "DESK", label: "TRADE TERMINAL" },
  "/analytics": { desk: "DESK", label: "PORTFOLIO & RISK" },
  "/bot": { desk: "ALGO", label: "AUTONOMOUS TRADING BOT" },
  "/alerts": { desk: "ALGO", label: "AUTOMATED SIGNALS" },
  "/chat": { desk: "INTEL", label: "NEURAL ASSISTANT" },
  "/leaderboard": { desk: "NETWORK", label: "GLOBAL RANKINGS" },
};

export default function TopBar({
  onMobileMenuToggle,
  onOpenNotifications,
  onOpenAbout,
  hasNewNotifs,
  isDark,
  toggleTheme,
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const { currency } = useCurrency();

  const [user, setUser] = useState(null);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const searchRef = useRef(null);

  // Fetch authenticated user info
  const fetchUser = async () => {
    try {
      const res = await api.get("/auth/me");
      if (res.data?.user) {
        setUser(res.data.user);
      }
    } catch (err) {}
  };

  useEffect(() => {
    fetchUser();
  }, []);

  // Close menus on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setUserMenuOpen(false);
      }
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setIsSearching(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Quick symbol search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    const timeout = setTimeout(async () => {
      try {
        const res = await api.get(`/stocks/search?q=${encodeURIComponent(searchQuery)}&limit=6`);
        setSearchResults(res.data?.results || []);
      } catch (err) {
        setSearchResults([]);
      }
    }, 200);
    return () => clearTimeout(timeout);
  }, [searchQuery]);

  const handleSelectSymbol = (sym) => {
    setSearchQuery("");
    setIsSearching(false);
    navigate(`/market?symbol=${sym}`);
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user_id");
    navigate("/login", { replace: true });
  };

  const routeInfo = ROUTE_LABELS[location.pathname] || { desk: "TERMINAL", label: "VIEW" };
  const initials = (user?.username?.[0] || user?.email?.[0] || "U").toUpperCase();

  return (
    <header className="h-14 bg-[#070b12] border-b border-white/10 px-3 md:px-5 flex items-center justify-between sticky top-8 z-30 select-none">
      {/* Left: Mobile Toggle & Breadcrumb Tag */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMobileMenuToggle}
          className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          title="Open Menu"
        >
          <Menu size={18} />
        </button>

        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="hidden sm:inline-block px-1.5 py-0.5 rounded bg-white/5 text-slate-400 font-semibold border border-white/5">
            {routeInfo.desk}
          </span>
          <span className="hidden sm:inline-block text-slate-600">//</span>
          <span className="text-white font-bold tracking-wider">{routeInfo.label}</span>
        </div>
      </div>

      {/* Center: Global Symbol Search */}
      <div className="relative hidden md:block w-64 lg:w-80" ref={searchRef}>
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 w-3.5 h-3.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setIsSearching(true);
            }}
            onFocus={() => setIsSearching(true)}
            placeholder="Search ticker, company... (Ctrl+K)"
            className="w-full bg-[#0d1424] border border-white/10 rounded-lg py-1.5 pl-8 pr-3 text-xs text-slate-200 placeholder-slate-500 font-mono focus:outline-none focus:border-cyan-500/50 transition-colors"
          />
        </div>

        {/* Search Results Dropdown */}
        {isSearching && searchResults.length > 0 && (
          <div className="absolute left-0 right-0 top-full mt-1.5 bg-[#0c1322] border border-white/10 rounded-lg shadow-xl shadow-black/50 py-1 z-50 overflow-hidden">
            {searchResults.map((item) => (
              <button
                key={item.symbol}
                onClick={() => handleSelectSymbol(item.symbol)}
                className="w-full px-3 py-1.5 text-left text-xs hover:bg-white/5 flex items-center justify-between transition-colors font-mono"
              >
                <div>
                  <span className="font-bold text-white mr-2">{item.symbol}</span>
                  <span className="text-slate-400 text-[11px] truncate">{item.company_name}</span>
                </div>
                <span className="text-[10px] text-cyan-400 bg-cyan-500/10 px-1 py-0.5 rounded">
                  {item.exchange}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Right: Currency, Paper Cash, Notifications, User Menu */}
      <div className="flex items-center gap-2 md:gap-3">
        {/* Currency Selector */}
        <div className="hidden sm:block">
          <CurrencySelector />
        </div>

        {/* Environment Indicator */}
        <div className="hidden md:flex items-center gap-1.5 px-2 py-1 rounded-lg text-[10px] font-mono font-semibold tracking-wider uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20" title="Trading environment: Paper Simulation (Safety Enforced)">
          <ShieldAlert size={12} className="text-amber-400" />
          <span>PAPER SIMULATION</span>
        </div>

        {/* Paper Balance Pill */}
        {user?.current_balance != null && (
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs font-mono">
            <Wallet size={13} className="text-emerald-400" />
            <span className="text-slate-400 text-[10px] uppercase">CASH:</span>
            <span className="font-bold text-emerald-400">
              ${Number(user.current_balance).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
        )}

        {/* Notification Bell */}
        <button
          onClick={onOpenNotifications}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors relative"
          title="Alerts & Notifications"
        >
          <Bell size={16} />
          {hasNewNotifs && (
            <span className="absolute top-1 right-1 w-2 h-2 bg-coral-500 rounded-full animate-ping" />
          )}
        </button>

        {/* Help / About Modal Trigger */}
        <button
          onClick={onOpenAbout}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          title="Terminal Architecture & About"
        >
          <HelpCircle size={16} />
        </button>

        {/* User Menu Dropdown */}
        <div className="relative" ref={userMenuRef}>
          <button
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            className="flex items-center gap-1.5 p-1 pl-1.5 pr-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
          >
            <div className="w-6 h-6 rounded-md bg-cyan-500/20 text-cyan-400 font-mono text-xs font-bold flex items-center justify-center">
              {initials}
            </div>
            <ChevronDown size={13} className="text-slate-400" />
          </button>

          {userMenuOpen && (
            <div className="absolute right-0 top-full mt-1.5 w-56 bg-[#0c1322] border border-white/10 rounded-lg shadow-xl shadow-black/60 py-1 z-50 overflow-hidden font-mono text-xs">
              <div className="px-3 py-2 border-b border-white/10">
                <p className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">OPERATOR</p>
                <p className="font-bold text-white truncate">{user?.username || user?.email}</p>
                {user?.current_balance != null && (
                  <p className="text-emerald-400 text-[11px] mt-0.5">
                    ${Number(user.current_balance).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </p>
                )}
              </div>

              <button
                onClick={() => {
                  setUserMenuOpen(false);
                  navigate("/analytics");
                }}
                className="w-full px-3 py-2 text-left text-slate-300 hover:bg-white/5 flex items-center gap-2"
              >
                <User size={14} className="text-slate-400" />
                <span>My Portfolio</span>
              </button>

              <div className="border-t border-white/10 my-1" />

              <button
                onClick={handleLogout}
                className="w-full px-3 py-2 text-left text-coral-400 hover:bg-coral-500/10 flex items-center gap-2 font-bold"
              >
                <LogOut size={14} />
                <span>Disconnect</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
