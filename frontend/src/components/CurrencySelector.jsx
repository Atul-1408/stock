import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check, Globe2 } from 'lucide-react';
import { useCurrency } from '../contexts/CurrencyContext';

const FLAG_EMOJI = {
    US: '🇺🇸', IN: '🇮🇳', EU: '🇪🇺', GB: '🇬🇧', JP: '🇯🇵', AU: '🇦🇺',
    CA: '🇨🇦', CH: '🇨🇭', CN: '🇨🇳', SG: '🇸🇬', HK: '🇭🇰', AE: '🇦🇪',
    BR: '🇧🇷', MX: '🇲🇽', ZA: '🇿🇦',
};

const CurrencySelector = () => {
    const { currency, currencies, setCurrency } = useCurrency();
    const [open, setOpen] = useState(false);
    const ref = useRef(null);

    // Close on outside click
    useEffect(() => {
        const handler = (e) => {
            if (ref.current && !ref.current.contains(e.target)) setOpen(false);
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    const current = currencies.find(c => c.code === currency) || { symbol: '$', code: 'USD' };

    return (
        <div ref={ref} className="relative">
            <button
                onClick={() => setOpen(!open)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 hover:border-accent/40 rounded-xl text-sm transition-all shadow-sm"
            >
                <Globe2 className="w-3.5 h-3.5 text-blue-500 dark:text-blue-400" />
                <span className="text-slate-900 dark:text-white font-bold">{current.symbol}</span>
                <span className="text-slate-500 dark:text-gray-400 text-xs font-medium">{currency}</span>
                <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
            </button>

            {open && (
                <div className="absolute right-0 top-full mt-2 w-72 bg-white dark:bg-slate-900 backdrop-blur-xl border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl shadow-black/10 dark:shadow-black/50 z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                    <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-800">
                        <h4 className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-[0.15em]">Select Currency</h4>
                    </div>
                    <div className="max-h-80 overflow-y-auto custom-scrollbar">
                        {currencies.map(c => {
                            const isActive = c.code === currency;
                            const flag = FLAG_EMOJI[c.country_code] || '🌐';
                            return (
                                <button
                                    key={c.code}
                                    onClick={() => { setCurrency(c.code); setOpen(false); }}
                                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-all hover:bg-slate-50 dark:hover:bg-slate-800/50 ${isActive ? 'bg-blue-500/5 dark:bg-blue-500/10' : ''
                                        }`}
                                >
                                    <span className="text-lg">{flag}</span>
                                    <span className="text-slate-900 dark:text-white font-bold text-sm w-8">{c.symbol}</span>
                                    <div className="flex-1 min-w-0">
                                        <span className="text-slate-900 dark:text-white text-sm font-bold">{c.code}</span>
                                        <span className="text-slate-400 dark:text-gray-500 text-xs ml-1.5 truncate font-medium">{c.name}</span>
                                    </div>
                                    {isActive && <Check className="w-4 h-4 text-blue-500 dark:text-blue-400 flex-shrink-0" />}
                                </button>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
};

export default CurrencySelector;
