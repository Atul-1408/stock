import React, { useState, useEffect, useRef, useCallback } from "react";
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { LayoutDashboard, PieChart, Bell, Trophy, MessageSquare, LogOut, User, ChevronDown, Settings, BarChart3, HelpCircle } from "lucide-react";
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import api from "./utils/api";

import DarkModeToggle from "./components/DarkModeToggle";
import Footer from "./components/Footer";
import ProtectedRoute from "./components/ProtectedRoute";
import TickerTape from "./components/TickerTape";
import NotificationPanel from "./components/NotificationPanel";
import AboutPanel from "./components/AboutPanel";

import Dashboard from "./pages/Dashboard";
import AnalyticsDashboard from "./pages/AnalyticsDashboard";
import AlertsPage from "./pages/AlertsPage";
import LeaderboardPage from "./pages/LeaderboardPage";
import ChatbotPanel from "./pages/ChatbotPanel";
import BotDashboard from "./components/bot/BotDashboard";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import MarketWatch from "./pages/MarketWatch";
import { CurrencyProvider } from "./contexts/CurrencyContext";
import CurrencySelector from "./components/CurrencySelector";
// ====================================================
// USER MENU: avatar + dropdown (logout, profile)
// ====================================================
function UserMenu({ isDark, toggleTheme }) {
  const [open, setOpen] = useState(false);
  const [user, setUser] = useState(null);
  const ref = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/auth/me")
      .then(r => setUser(r.data.user))
      .catch(() => { });
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleLogout = useCallback(() => {
    localStorage.removeItem("token");
    navigate("/login", { replace: true });
  }, [navigate]);

  const initials = user
    ? ((user.first_name?.[0] || "") + (user.last_name?.[0] || "") || user.email?.[0] || "U").toUpperCase()
    : "U";

  const displayName = user
    ? (user.first_name ? `${user.first_name} ${user.last_name || ""}`.trim() : user.email)
    : "Loading…";

  return (
    <div className="flex items-center gap-3" ref={ref}>
      {/* Dark mode toggle */}
      <DarkModeToggle isDark={isDark} toggle={toggleTheme} />

      {/* Avatar button */}
      <div className="relative">
        <button
          onClick={() => setOpen(o => !o)}
          className="flex items-center gap-2 pl-2 pr-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 hover:border-accent/50 transition-all group"
        >
          <div className="w-7 h-7 rounded-lg bg-accent/20 text-accent flex items-center justify-center text-xs font-black">
            {initials}
          </div>
          <span className="hidden sm:block text-sm font-bold text-slate-700 dark:text-slate-200 max-w-[120px] truncate">
            {displayName}
          </span>
          <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
        </button>

        {/* Dropdown */}
        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="absolute right-0 mt-2 w-56 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-2xl shadow-black/20 overflow-hidden z-50"
            >
              {/* User info header */}
              <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-800">
                <p className="text-xs text-slate-500 font-semibold">Signed in as</p>
                <p className="text-sm font-black text-slate-900 dark:text-white truncate mt-0.5">{displayName}</p>
                {user?.email && <p className="text-xs text-slate-400 truncate">{user.email}</p>}
              </div>

              {/* Balance */}
              {user?.current_balance != null && (
                <div className="px-4 py-2 border-b border-slate-100 dark:border-slate-800">
                  <p className="text-xs text-slate-500 font-semibold uppercase tracking-wide">Paper Balance</p>
                  <p className="text-base font-black text-accent">
                    ${Number(user.current_balance).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </p>
                </div>
              )}

              {/* Menu items */}
              <div className="p-1.5">
                <button
                  onClick={() => { setOpen(false); navigate("/analytics"); }}
                  className="w-full flex items-center gap-3 px-3 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors font-semibold"
                >
                  <User className="w-4 h-4 text-slate-400" />
                  My Analytics
                </button>
                <button
                  onClick={() => { setOpen(false); navigate("/alerts"); }}
                  className="w-full flex items-center gap-3 px-3 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors font-semibold"
                >
                  <Settings className="w-4 h-4 text-slate-400" />
                  Alerts & Settings
                </button>
              </div>

              {/* Logout */}
              <div className="p-1.5 border-t border-slate-100 dark:border-slate-800">
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-3 py-2 text-sm text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-lg transition-colors font-bold"
                >
                  <LogOut className="w-4 h-4" />
                  Sign Out
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}


const Navigation = () => {
  const location = useLocation();
  const tabs = [
    { id: 'dashboard', label: 'Markets', path: '/dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: 'market', label: 'Trade', path: '/market', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'bot', label: 'Bot', path: '/bot', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'analytics', label: 'Analytics', path: '/analytics', icon: <PieChart className="w-4 h-4" /> },
    { id: 'alerts', label: 'Alerts', path: '/alerts', icon: <Bell className="w-4 h-4" /> },
    { id: 'leaderboard', label: 'Elite', path: '/leaderboard', icon: <Trophy className="w-4 h-4" /> },
    { id: 'chat', label: 'AI AI', path: '/chat', icon: <MessageSquare className="w-4 h-4" /> },
  ];

  return (
    <div className="flex bg-slate-200/50 dark:bg-slate-800/50 p-1 rounded-xl w-fit mb-8 overflow-x-auto no-scrollbar max-w-full">
      {tabs.map((tab) => {
        const isActive = location.pathname === tab.path;
        return (
          <Link
            key={tab.id}
            to={tab.path}
            className={`flex items-center gap-2 px-6 py-2 rounded-lg text-sm font-bold transition-all whitespace-nowrap ${isActive
              ? "bg-white dark:bg-slate-700 shadow-lg text-accent scale-[1.02]"
              : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              }`}
          >
            {tab.icon}
            {tab.label}
          </Link>
        );
      })}
    </div>
  );
};

function App() {
  const [isDark, setIsDark] = useState(true);
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [isAboutOpen, setIsAboutOpen] = useState(false);
  const [hasNewNotifs, setHasNewNotifs] = useState(false);

  useEffect(() => {
    const checkBotAlerts = async () => {
      try {
        const res = await api.get('/alerts/bot');
        if (res.data.alerts.length > 0) {
          // If the most recent one is newer than 5 minutes, show a dot
          const lastNotif = new Date(res.data.alerts[0].triggered_at);
          const now = new Date();
          if (now - lastNotif < 300000) { // 5 minutes
            setHasNewNotifs(true);
          }
        }
      } catch (err) {}
    };
    checkBotAlerts();
    const interval = setInterval(checkBotAlerts, 60000); // Check every minute
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const savedTheme = localStorage.getItem("theme");
    const initialTheme = savedTheme ? savedTheme === "dark" : true;
    setIsDark(initialTheme);
    document.documentElement.setAttribute("data-theme", initialTheme ? "dark" : "light");
  }, []);

  const toggleTheme = () => {
    const nextTheme = !isDark;
    setIsDark(nextTheme);
    document.documentElement.setAttribute("data-theme", nextTheme ? "dark" : "light");
    localStorage.setItem("theme", nextTheme ? "dark" : "light");
  };

  const PageWrapper = ({ children, subtitle, breadcrumb }) => (
    <ProtectedRoute>
      <div className="w-full max-w-full px-3 md:px-6 xl:px-10 py-6">
        <header className="grid grid-cols-1 md:grid-cols-3 items-center mb-10 gap-4">
          {/* Left: Help/About Button */}
          <div className="flex items-center justify-center md:justify-start">
            <button
              onClick={() => setIsAboutOpen(true)}
              className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-500 hover:text-accent hover:bg-accent/10 transition-all"
              title="About & Support"
            >
              <HelpCircle className="w-5 h-5" />
            </button>
          </div>

          {/* Center: Branding */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-center"
          >
            <p className="text-accent text-xs font-black tracking-widest uppercase opacity-80 flex items-center justify-center gap-2">
              <span className="w-2 h-2 bg-accent rounded-full animate-pulse"></span>
              {breadcrumb || "Market Intelligence"}
            </p>
            <h1 className="text-3xl md:text-4xl font-black mt-1 tracking-tight text-slate-900 dark:text-white">
              Stock <span className="text-accent">Sense</span>
            </h1>
            <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm leading-relaxed font-medium hidden md:block">
              {subtitle || "The definitive stock intelligence platform powered by sentiment AI."}
            </p>
          </motion.div>

          {/* Right: currency + dark mode + user menu */}
          <div className="flex items-center justify-center md:justify-end gap-3">
            <CurrencySelector />
            
            {/* Notification Bell */}
            <button
              onClick={() => { setIsNotifOpen(true); setHasNewNotifs(false); }}
              className={`p-2 rounded-xl transition-all relative ${hasNewNotifs ? 'bg-rose-500/10 text-rose-500 animate-pulse' : 'bg-slate-100 dark:bg-slate-800 text-slate-500 hover:text-accent hover:bg-accent/10'}`}
            >
              <Bell className="w-5 h-5" />
              {hasNewNotifs && (
                <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-rose-500 border-2 border-white dark:border-[#0A0B10] rounded-full" />
              )}
            </button>

            <UserMenu isDark={isDark} toggleTheme={toggleTheme} />
          </div>
        </header>

        <div className="flex justify-center mb-8">
          <Navigation />
        </div>

        <NotificationPanel isOpen={isNotifOpen} onClose={() => setIsNotifOpen(false)} />
        <AboutPanel isOpen={isAboutOpen} onClose={() => setIsAboutOpen(false)} />

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          {children}
        </motion.div>

        <Footer />
      </div>
    </ProtectedRoute>
  );

  return (
    <CurrencyProvider>
      <BrowserRouter>
        {/* ── Sticky Ticker Tape: fixed at top, always visible on scroll ── */}
        <TickerTape />
        <div className="min-h-screen transition-colors duration-400 bg-slate-50 dark:bg-[#0A0B10]" style={{ paddingTop: 40 }}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />

            <Route
              path="/dashboard"
              element={
                <PageWrapper breadcrumb="Market Intelligence">
                  <Dashboard />
                </PageWrapper>
              }
            />

            <Route
              path="/market"
              element={
                <PageWrapper breadcrumb="Trade Terminal" subtitle="Professional broker-style trading with real market data.">
                  <MarketWatch />
                </PageWrapper>
              }
            />

            <Route
              path="/analytics"
              element={
                <PageWrapper
                  breadcrumb="Portfolio Insights"
                  subtitle="In-depth portfolio performance, risk assessments, and historical benchmarks."
                >
                  <AnalyticsDashboard />
                </PageWrapper>
              }
            />

            <Route
              path="/alerts"
              element={
                <PageWrapper
                  breadcrumb="Automated Signals"
                  subtitle="Configure sentiment triggers and price targets for real-time notifications."
                >
                  <AlertsPage />
                </PageWrapper>
              }
            />

            <Route
              path="/leaderboard"
              element={
                <PageWrapper
                  breadcrumb="Global Rankings"
                  subtitle="Compete with the community's top signal intelligence nodes."
                >
                  <LeaderboardPage />
                </PageWrapper>
              }
            />

            <Route
              path="/chat"
              element={
                <PageWrapper
                  breadcrumb="Neural Hub"
                  subtitle="Context-aware AI Trading Assistant powered by Claude 3.5 Sonnet."
                >
                  <ChatbotPanel />
                </PageWrapper>
              }
            />

            <Route
              path="/bot"
              element={
                <PageWrapper breadcrumb="Autonomous Trading Bot" subtitle="AI-powered trading with sentiment, technical, and ML analysis.">
                  <BotDashboard />
                </PageWrapper>
              }
            />

            <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Routes>

          <ToastContainer
            position="bottom-right"
            theme={isDark ? "dark" : "light"}
            autoClose={3000}
          />
        </div>
      </BrowserRouter>
    </CurrencyProvider>
  );
}

export default App;
