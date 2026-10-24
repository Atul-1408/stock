import React from "react";

function Footer() {
  return (
    <footer className="py-6 border-t border-terminal-800 bg-terminal-950/60 font-mono text-2xs text-slate-400">
      <div className="max-w-7xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-bold text-slate-200 uppercase">Sovereign Intelligence</span>
          <span>&bull;</span>
          <span>Institutional Financial Terminal</span>
        </div>
        <div>
          Simulation & Execution Desk &bull; All real-time telemetry encrypted
        </div>
      </div>
    </footer>
  );
}

export default Footer;
