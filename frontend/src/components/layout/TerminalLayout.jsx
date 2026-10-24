import React, { useState } from "react";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import TickerTape from "../TickerTape";
import NotificationPanel from "../NotificationPanel";
import AboutPanel from "../AboutPanel";
import Footer from "../Footer";

export default function TerminalLayout({
  children,
  hasNewNotifs,
  isNotifOpen,
  setIsNotifOpen,
  isAboutOpen,
  setIsAboutOpen,
  isDark,
  toggleTheme,
}) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#070b12] text-slate-100 flex flex-col font-sans">
      {/* 1. Global Real-time Ticker Tape (Fixed top strip) */}
      <TickerTape />

      <div className="flex flex-1 pt-8">
        {/* 2. Collapsible Desktop / Mobile Sidebar */}
        <Sidebar
          isCollapsed={isCollapsed}
          setIsCollapsed={setIsCollapsed}
          isMobileOpen={isMobileOpen}
          setIsMobileOpen={setIsMobileOpen}
        />

        {/* 3. Main Terminal Area */}
        <div
          className={`flex-1 flex flex-col min-w-0 transition-all duration-200
            ${isCollapsed ? "lg:ml-[68px]" : "lg:ml-[240px]"}
          `}
        >
          {/* Top Bar Header */}
          <TopBar
            onMobileMenuToggle={() => setIsMobileOpen(true)}
            onOpenNotifications={() => setIsNotifOpen(true)}
            onOpenAbout={() => setIsAboutOpen(true)}
            hasNewNotifs={hasNewNotifs}
            isDark={isDark}
            toggleTheme={toggleTheme}
          />

          {/* Main View Container */}
          <main className="flex-1 p-3 md:p-6 max-w-full">
            {children}
          </main>

          {/* Minimal Terminal Footer */}
          <Footer />
        </div>
      </div>

      {/* Slide-over Drawers / Modals */}
      <NotificationPanel isOpen={isNotifOpen} onClose={() => setIsNotifOpen(false)} />
      <AboutPanel isOpen={isAboutOpen} onClose={() => setIsAboutOpen(false)} />
    </div>
  );
}
