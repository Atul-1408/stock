import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Info, HelpCircle, Mail, MessageCircle, Shield, Zap, BarChart3, Brain, QrCode, ExternalLink } from 'lucide-react';
import QRCode from 'react-qr-code';

const AboutPanel = ({ isOpen, onClose }) => {
    const features = [
        {
            icon: <Brain className="w-5 h-5 text-purple-500" />,
            title: "Sentiment AI",
            desc: "Our neural engine analyzes thousands of news headlines in real-time to gauge market mood."
        },
        {
            icon: <BarChart3 className="w-5 h-5 text-blue-500" />,
            title: "Broker-Style Trading",
            desc: "Execute paper trades with real market data to test your strategies without risk."
        },
        {
            icon: <Zap className="w-5 h-5 text-amber-500" />,
            title: "Smart Alerts",
            desc: "Set custom triggers for price movements and sentiment shifts to stay ahead."
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
                        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[100]"
                    />

                    {/* Panel */}
                    <motion.div
                        initial={{ x: '-100%' }}
                        animate={{ x: 0 }}
                        exit={{ x: '-100%' }}
                        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                        className="fixed left-0 top-10 bottom-0 w-full max-w-sm bg-white dark:bg-[#0F1117] shadow-2xl z-[101] flex flex-col"
                    >
                        <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-blue-500/10 rounded-lg">
                                    <HelpCircle className="w-5 h-5 text-blue-500" />
                                </div>
                                <div>
                                    <h3 className="font-black text-slate-900 dark:text-white">About the App</h3>
                                    <p className="text-xs text-slate-500 font-bold uppercase tracking-widest">Guide & Support</p>
                                </div>
                            </div>
                            <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors">
                                <X className="w-5 h-5 text-slate-400" />
                            </button>
                        </div>

                        <div className="flex-1 overflow-y-auto p-6 space-y-8 no-scrollbar">
                            {/* How it Works */}
                            <section className="space-y-4">
                                <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                                    <Shield className="w-3 h-3" /> How it Works
                                </h4>
                                <div className="space-y-4">
                                    {features.map((f, i) => (
                                        <div key={i} className="flex gap-4 p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-700/50">
                                            <div className="flex-shrink-0 mt-1">{f.icon}</div>
                                            <div>
                                                <p className="text-sm font-black text-slate-900 dark:text-white">{f.title}</p>
                                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                                                    {f.desc}
                                                </p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </section>

                            {/* Telegram Bot QR */}
                            <section className="space-y-4">
                                <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                                    <QrCode className="w-3 h-3" /> Telegram Bot
                                </h4>
                                <div className="p-5 rounded-2xl bg-blue-500/5 border border-blue-500/10 flex flex-col items-center gap-4">
                                    <div className="bg-white p-3 rounded-xl shadow-lg shadow-blue-500/10 border border-slate-100">
                                        <div style={{ height: "auto", margin: "0 auto", maxWidth: 120, width: "100%" }}>
                                            <QRCode
                                                size={256}
                                                style={{ height: "auto", maxWidth: "100%", width: "100%" }}
                                                value="https://t.me/Trederrrrr_bot"
                                                viewBox={`0 0 256 256`}
                                            />
                                        </div>
                                    </div>
                                    <div className="text-center">
                                        <p className="text-sm font-bold text-slate-900 dark:text-white mb-1">Join the Channel</p>
                                        <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">Scan to get direct signals via Telegram</p>
                                        <a 
                                            href="https://t.me/Trederrrrr_bot" 
                                            target="_blank" 
                                            rel="noopener noreferrer"
                                            className="inline-flex items-center gap-2 px-4 py-2 bg-[#229ED9] hover:bg-[#1c87ba] text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-blue-500/20"
                                        >
                                            <ExternalLink className="w-3 h-3" /> Launch Bot
                                        </a>
                                    </div>
                                </div>
                            </section>

                            {/* Contact Support */}
                            <section className="space-y-4">
                                <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                                    <Mail className="w-3 h-3" /> Contact Support
                                </h4>
                                <div className="p-5 rounded-2xl bg-accent/5 border border-accent/10 space-y-4">
                                    <p className="text-sm text-slate-600 dark:text-slate-300">
                                        Need help with your account or have a feature request? Our team is available 24/7.
                                    </p>
                                    <div className="space-y-3">
                                        <a href="mailto:support@stocksense.ai" className="flex items-center gap-3 p-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 hover:border-accent/50 transition-all group">
                                            <Mail className="w-4 h-4 text-accent" />
                                            <span className="text-xs font-bold text-slate-700 dark:text-slate-200">support@stocksense.ai</span>
                                        </a>
                                        <div className="flex items-center gap-3 p-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 group">
                                            <MessageCircle className="w-4 h-4 text-emerald-500" />
                                            <span className="text-xs font-bold text-slate-700 dark:text-slate-200">Live Chat (Elite Only)</span>
                                        </div>
                                    </div>
                                </div>
                            </section>
                        </div>

                        <div className="p-6 bg-slate-50 dark:bg-slate-800/20 border-t border-slate-100 dark:border-slate-800">
                            <p className="text-[10px] text-center text-slate-500 font-bold uppercase tracking-widest">
                                Version 2.4.0 • Built with ❤️ for Traders
                            </p>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
};

export default AboutPanel;
