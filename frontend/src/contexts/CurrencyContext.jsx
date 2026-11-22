import React, { createContext, useState, useContext, useEffect, useCallback, useRef } from 'react';
import api from '../utils/api';
import { formatCurrency } from '../utils/currency';

const DEFAULT_RATES = {
    USD: 1.0,
    INR: 86.5,
    EUR: 0.92,
    GBP: 0.79,
    JPY: 155.0,
    AUD: 1.55,
    CAD: 1.40,
    CHF: 0.90,
    CNY: 7.25,
    SGD: 1.35,
    HKD: 7.80,
    AED: 3.67,
    BRL: 5.80,
    MXN: 20.5,
    ZAR: 18.2,
};

const DEFAULT_CURRENCIES = [
    { code: 'USD', name: 'US Dollar', symbol: '$', country_code: 'US' },
    { code: 'INR', name: 'Indian Rupee', symbol: '₹', country_code: 'IN' },
    { code: 'EUR', name: 'Euro', symbol: '€', country_code: 'EU' },
    { code: 'GBP', name: 'British Pound', symbol: '£', country_code: 'GB' },
    { code: 'JPY', name: 'Japanese Yen', symbol: '¥', country_code: 'JP' },
    { code: 'AUD', name: 'Australian Dollar', symbol: 'A$', country_code: 'AU' },
    { code: 'CAD', name: 'Canadian Dollar', symbol: 'C$', country_code: 'CA' },
    { code: 'CHF', name: 'Swiss Franc', symbol: 'CHF ', country_code: 'CH' },
    { code: 'CNY', name: 'Chinese Yuan', symbol: '¥', country_code: 'CN' },
    { code: 'SGD', name: 'Singapore Dollar', symbol: 'S$', country_code: 'SG' },
    { code: 'HKD', name: 'Hong Kong Dollar', symbol: 'HK$', country_code: 'HK' },
    { code: 'AED', name: 'UAE Dirham', symbol: 'AED ', country_code: 'AE' },
    { code: 'BRL', name: 'Brazilian Real', symbol: 'R$', country_code: 'BR' },
    { code: 'MXN', name: 'Mexican Peso', symbol: 'MX$', country_code: 'MX' },
    { code: 'ZAR', name: 'South African Rand', symbol: 'R', country_code: 'ZA' },
];

const CurrencyContext = createContext({
    currency: 'USD',
    currencies: DEFAULT_CURRENCIES,
    rates: DEFAULT_RATES,
    setCurrency: () => { },
    convertPrice: (amount, fromCurrency) => amount,
    formatPrice: (amount, fromCurrency) => `$${amount}`,
    loading: false,
});

export const useCurrency = () => useContext(CurrencyContext);

/**
 * Determine the native currency of a stock based on its ticker symbol.
 * .NS suffix = INR (India), -USD suffix or crypto = USD, otherwise USD.
 */
export function getNativeCurrency(ticker) {
    if (!ticker) return 'USD';
    const t = ticker.toUpperCase();
    if (t.endsWith('.NS') || t.endsWith('.BO')) return 'INR';
    if (t.endsWith('.L')) return 'GBP';
    if (t.endsWith('.T')) return 'JPY';
    if (t.endsWith('.HK')) return 'HKD';
    if (t.endsWith('.AX')) return 'AUD';
    return 'USD';
}

export function CurrencyProvider({ children }) {
    const [currency, setCurrencyState] = useState(() => {
        return localStorage.getItem('preferredCurrency') || 'USD';
    });
    const [currencies, setCurrencies] = useState(DEFAULT_CURRENCIES);
    const [rates, setRates] = useState(DEFAULT_RATES);
    const [loading, setLoading] = useState(true);
    const ratesRef = useRef(rates);
    ratesRef.current = rates;
    const initOnceRef = useRef(false);

    // Load available currencies and exchange rates on mount
    useEffect(() => {
        if (initOnceRef.current) return;
        initOnceRef.current = true;
        const init = async () => {
            // Fetch currency list
            try {
                const { data } = await api.get('/currency/list');
                if (data.currencies && data.currencies.length > 0) {
                    setCurrencies(data.currencies);
                }
            } catch (err) {
                console.error('Failed to load currencies, using defaults:', err);
            }

            // Fetch exchange rates (USD-based)
            try {
                const { data } = await api.get('/currency/rates');
                if (data.rates) {
                    setRates((prev) => ({ ...prev, ...data.rates }));
                }
            } catch (err) {
                console.error('Failed to load exchange rates, using defaults:', err);
            }

            // Try to get user preference from backend (only if user is authenticated)
            try {
                const token = localStorage.getItem('token');
                const isValidToken = token && token !== 'undefined' && token !== 'null';
                if (isValidToken) {
                    const { data } = await api.get('/user/currency');
                    if (data.currency) {
                        setCurrencyState(data.currency);
                        localStorage.setItem('preferredCurrency', data.currency);
                    }
                }
            } catch (err) {
                // Not logged in or error, try auto-detect
                const saved = localStorage.getItem('preferredCurrency');
                if (!saved) {
                    try {
                        const { data } = await api.get('/currency/detect');
                        if (data.currency) {
                            setCurrencyState(data.currency);
                            localStorage.setItem('preferredCurrency', data.currency);
                        }
                    } catch (detectErr) {}
                }
            }
            setLoading(false);
        };
        init();
    }, []);

    const setCurrency = useCallback(async (code) => {
        setCurrencyState(code);
        localStorage.setItem('preferredCurrency', code);
        try {
            const token = localStorage.getItem('token');
            const isValidToken = token && token !== 'undefined' && token !== 'null';
            if (isValidToken) {
                await api.put('/user/currency', { currency: code });
            }
        } catch (err) {
            // Not logged in, stored locally
        }
    }, []);

    /**
     * Convert an amount from a given currency to the user's selected currency.
     * Uses triangular conversion via USD: amount → USD → target currency.
     */
    const convertPrice = useCallback((amount, fromCurrency = 'USD') => {
        if (amount == null || isNaN(amount)) return amount;
        const currentRates = { ...DEFAULT_RATES, ...ratesRef.current };
        const toCurrency = currency || localStorage.getItem('preferredCurrency') || 'USD';
        const numAmount = Number(amount);
        if (!fromCurrency || fromCurrency === toCurrency) return numAmount;

        const fromRate = currentRates[fromCurrency] || 1.0;
        const toRate = currentRates[toCurrency] || 1.0;

        if (!fromRate || !toRate) return numAmount;

        const amountInUSD = numAmount / fromRate;
        return amountInUSD * toRate;
    }, [currency]);

    /**
     * Format and convert an amount into the active preferred currency.
     */
    const formatPrice = useCallback((amount, fromCurrency = 'USD') => {
        if (amount == null || isNaN(amount)) return '—';
        const converted = convertPrice(Number(amount), fromCurrency);
        return formatCurrency(converted, currency);
    }, [currency, convertPrice]);

    return (
        <CurrencyContext.Provider value={{ currency, currencies, rates, setCurrency, convertPrice, formatPrice, loading }}>
            {children}
        </CurrencyContext.Provider>
    );
}

export default CurrencyContext;
