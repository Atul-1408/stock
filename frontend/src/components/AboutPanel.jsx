import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, HelpCircle, Mail, MessageCircle, Shield, Zap, BarChart3, Brain, QrCode, ExternalLink, Terminal } from "lucide-react";
import QRCode from "react-qr-code";

const AboutPanel = ({ isOpen, onClose }) => {
  const features = [
    {
      icon: <Brain className="w-4 h-4 text-terminal-cyan" />,
      title: "NLP Sentiment Core",
      desc: "Real-time semantic vector processing over live financial wires to compute polarity & confidence."
    },
    {
      icon: <BarChart3 className="w-4 h-4 text-terminal-emerald" />,
      title: "Paper Trade Sandbox",
      desc: "Institutional simulated execution using live tick data to test discretionary and algorithmic alphas."
    },
    {
      icon: <Zap className="w-4 h-4 text-amber-400" />,
      title: "Dynamic Alert Rules",
      desc: "Instant threshold triggers dispatched across web sockets and telegram bots on price/sentiment spikes."
    }
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-xs z-[100]"
          />

          {/* Drawer Panel */}
          <motion.div
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 240 }}
            className="fixed left-0 top-0 bottom-0 w-full max-w-sm bg-[#0c1322] border-r border-terminal-800 shadow-2xl z-[101] flex flex-col font-mono"
          >
            {/* Header */}
            <div className="p-4 border-b border-terminal-800 flex justify-between items-center bg-terminal-950/60">
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 bg-terminal-cyan/10 border border-terminal-cyan/30 rounded text-terminal-cyan">
                  <Terminal className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-100">
                    Desk Documentation
                  </h3>
                  <p className="text-2xs text-slate-400 uppercase tracking-wider">
                    Sovereign Intelligence Architecture
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded hover:bg-terminal-800 text-slate-400 hover:text-slate-200 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Scrollable Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-6">
              {/* Architecture Pillars */}
              <section className="space-y-3">
                <div className="text-2xs font-bold uppercase tracking-widest text-slate-400 flex items-center gap-1.5">
                  <Shield className="w-3 h-3 text-terminal-cyan" /> Core Engine Architecture
                </div>
                <div className="space-y-2.5">
                  {features.map((f, i) => (
                    <div
                      key={i}
                      className="p-3 rounded border border-terminal-800 bg-terminal-950/50 hover:border-terminal-700 transition-colors"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        {f.icon}
                        <span className="text-xs font-bold text-slate-100 uppercase">{f.title}</span>
                      </div>
                      <p className="text-2xs text-slate-300 leading-relaxed font-sans">{f.desc}</p>
                    </div>
                  ))}
                </div>
              </section>

              {/* Telegram Feed */}
              <section className="space-y-3">
                <div className="text-2xs font-bold uppercase tracking-widest text-slate-400 flex items-center gap-1.5">
                  <QrCode className="w-3 h-3 text-terminal-emerald" /> Telegram Intelligence Node
                </div>
                <div className="p-4 rounded border border-terminal-800 bg-terminal-950/60 flex flex-col items-center gap-3">
                  <div className="bg-white p-2.5 rounded border border-white/20">
                    <QRCode
                      size={110}
                      value="https://t.me/Trederrrrr_bot"
                      viewBox="0 0 256 256"
                    />
                  </div>
                  <div className="text-center">
                    <p className="text-xs font-bold text-slate-100 uppercase mb-0.5">Automated Signal Channel</p>
                    <p className="text-2xs text-slate-400 mb-3 font-sans">Scan or open bot for real-time mobile order alerts.</p>
                    <a
                      href="https://t.me/Trederrrrr_bot"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-terminal-cyan/15 border border-terminal-cyan/40 hover:bg-terminal-cyan/25 text-terminal-cyan rounded text-2xs uppercase font-bold tracking-wider transition-all"
                    >
                      <ExternalLink className="w-3 h-3" /> Connect Node
                    </a>
                  </div>
                </div>
              </section>

              {/* Support */}
              <section className="space-y-3">
                <div className="text-2xs font-bold uppercase tracking-widest text-slate-400 flex items-center gap-1.5">
                  <Mail className="w-3 h-3 text-slate-400" /> Engineering Support
                </div>
                <div className="p-3 rounded border border-terminal-800 bg-terminal-950/40 space-y-2">
                  <div className="flex items-center gap-2 text-2xs text-slate-300">
                    <Mail className="w-3.5 h-3.5 text-terminal-cyan" />
                    <span>support@sovereign-intelligence.internal</span>
                  </div>
                  <div className="flex items-center gap-2 text-2xs text-slate-400">
                    <MessageCircle className="w-3.5 h-3.5 text-terminal-emerald" />
                    <span>Real-time Chat via AI Intelligence Tab</span>
                  </div>
                </div>
              </section>
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-terminal-800 bg-terminal-950/60 text-center text-2xs uppercase tracking-wider text-slate-400">
              Terminal Release v3.0.0 &bull; Institutional Stack
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default AboutPanel;
