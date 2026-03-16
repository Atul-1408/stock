import React, { createContext, useState, useContext, useEffect, useCallback, useRef } from 'react';
import api from '../utils/api';

const CurrencyContext = createContext({
    currency: 'USD',
    currencies: [],
    rates: {},         // USD-based rates: { INR: 90.97, EUR: 0.92, ... }
    setCurrency: () => { },
    convertPrice: (amount, fromCurrency) => amount,
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
    const [currencies, setCurrencies] = useState([]);
    const [rates, setRates] = useState({});     // { INR: 90.97, EUR: 0.92, USD: 1.0, ... }
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
                setCurrencies(data.currencies || []);
            } catch (err) {
                console.error('Failed to load currencies:', err);
            }

            // Fetch exchange rates (USD-based)
            try {
                const { data } = await api.get('/currency/rates');
                if (data.rates) {
                    setRates(data.rates);
                }
            } catch (err) {
                console.error('Failed to load exchange rates:', err);
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
                console.error('User currency fetch failed:', err);
                // Not logged in or error, try auto-detect
                const saved = localStorage.getItem('preferredCurrency');
                if (!saved) {
                    try {
                        const { data } = await api.get('/currency/detect');
                        if (data.currency) {
                            setCurrencyState(data.currency);
                            localStorage.setItem('preferredCurrency', data.currency);
                        }
                    } catch (detectErr) {
                        console.error('Auto-detection failed:', detectErr);
                        // Use default USD
                    }
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
            console.error('Failed to save user currency preference:', err);
            // Not logged in, just use localStorage
        }
    }, []);

    /**
     * Convert an amount from a given currency to the user's selected currency.
     * Uses triangular conversion via USD: amount → USD → target currency.
     *
     * @param {number} amount - The amount to convert
     * @param {string} fromCurrency - Source currency code (e.g. 'INR', 'USD')
     * @returns {number} - Converted amount
     */
    const convertPrice = useCallback((amount, fromCurrency) => {
        if (amount == null || isNaN(amount)) return amount;
        const currentRates = ratesRef.current;
        const toCurrency = localStorage.getItem('preferredCurrency') || 'USD';
        if (!fromCurrency || fromCurrency === toCurrency) return amount;
        if (!currentRates || Object.keys(currentRates).length === 0) return amount;

        // All rates are USD-based: rates[X] = how many X per 1 USD
        const fromRate = currentRates[fromCurrency];  // e.g. INR = 90.97
        const toRate = currentRates[toCurrency];      // e.g. EUR = 0.92

        if (!fromRate || !toRate) return amount;

        // Convert: amount in from → USD → to
        const amountInUSD = amount / fromRate;
        return amountInUSD * toRate;
    }, []);

    return (
        <CurrencyContext.Provider value={{ currency, currencies, rates, setCurrency, convertPrice, loading }}>
            {children}
        </CurrencyContext.Provider>
    );
}

export default CurrencyContext;
