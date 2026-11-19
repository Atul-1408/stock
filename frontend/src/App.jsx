import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

import api from "./utils/api";
import ProtectedRoute from "./components/ProtectedRoute";
import TerminalLayout from "./components/layout/TerminalLayout";

import Dashboard from "./pages/Dashboard";
import AnalyticsDashboard from "./pages/AnalyticsDashboard";
import AlertsPage from "./pages/AlertsPage";
import LeaderboardPage from "./pages/LeaderboardPage";
import ChatbotPanel from "./pages/ChatbotPanel";
import BotDashboard from "./components/bot/BotDashboard";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import MarketWatch from "./pages/MarketWatch";
import LandingPage from "./pages/LandingPage";
import NotFoundPage from "./pages/NotFoundPage";
import Seo from "./utils/seo";
import { CurrencyProvider } from "./contexts/CurrencyContext";

function App() {
  const [isDark, setIsDark] = useState(true);
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [isAboutOpen, setIsAboutOpen] = useState(false);
  const [hasNewNotifs, setHasNewNotifs] = useState(false);

  useEffect(() => {
    const checkBotAlerts = async () => {
      const token = localStorage.getItem("token");
      if (!token || token === "undefined" || token === "null") return;

      try {
        const res = await api.get("/alerts/bot");
        if (res.data?.alerts && res.data.alerts.length > 0) {
          const lastNotif = new Date(res.data.alerts[0].triggered_at);
          const now = new Date();
          if (now - lastNotif < 300000) {
            setHasNewNotifs(true);
          }
        }
      } catch (err) {}
    };
    checkBotAlerts();
    const interval = setInterval(checkBotAlerts, 60000);
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

  const renderProtectedView = (Component, title = "Terminal") => (
    <ProtectedRoute>
      <Seo title={title} noindex />
      <TerminalLayout
        hasNewNotifs={hasNewNotifs}
        isNotifOpen={isNotifOpen}
        setIsNotifOpen={setIsNotifOpen}
        isAboutOpen={isAboutOpen}
        setIsAboutOpen={setIsAboutOpen}
        isDark={isDark}
        toggleTheme={toggleTheme}
      >
        <Component />
      </TerminalLayout>
    </ProtectedRoute>
  );

  return (
    <CurrencyProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-[#070b12] text-slate-100 font-sans">
          <Routes>
            {/* Public Auth Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />

            {/* Institutional Protected Routes */}
            <Route path="/dashboard" element={renderProtectedView(Dashboard, "Dashboard")} />
            <Route path="/market" element={renderProtectedView(MarketWatch, "Market Watch")} />
            <Route path="/analytics" element={renderProtectedView(AnalyticsDashboard, "Analytics")} />
            <Route path="/alerts" element={renderProtectedView(AlertsPage, "Alerts")} />
            <Route path="/leaderboard" element={renderProtectedView(LeaderboardPage, "Leaderboard")} />
            <Route path="/chat" element={renderProtectedView(ChatbotPanel, "AI Assistant")} />
            <Route path="/bot" element={renderProtectedView(BotDashboard, "Trading Bot")} />

            {/* Public landing page + real 404 (no more redirect loop to /login) */}
            <Route path="/" element={<LandingPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>

          <ToastContainer
            position="bottom-right"
            theme="dark"
            autoClose={3000}
            toastClassName="!bg-[#0c1322] !text-white !border !border-white/10 !font-mono !text-xs !shadow-2xl"
          />
        </div>
      </BrowserRouter>
    </CurrencyProvider>
  );
}

export default App;
