/**
 * Currency formatting utilities.
 * Supports Indian numbering system (lakhs/crores), Japanese yen (no decimals), etc.
 */

const CURRENCY_FORMATS = {
    USD: { symbol: '$', decimals: 2 },
    INR: { symbol: '₹', decimals: 2 },
    EUR: { symbol: '€', decimals: 2 },
    GBP: { symbol: '£', decimals: 2 },
    JPY: { symbol: '¥', decimals: 0 },
    AUD: { symbol: 'A$', decimals: 2 },
    CAD: { symbol: 'C$', decimals: 2 },
    CHF: { symbol: 'CHF ', decimals: 2 },
    CNY: { symbol: '¥', decimals: 2 },
    SGD: { symbol: 'S$', decimals: 2 },
    HKD: { symbol: 'HK$', decimals: 2 },
    AED: { symbol: 'AED ', decimals: 2 },
    BRL: { symbol: 'R$', decimals: 2 },
    MXN: { symbol: 'MX$', decimals: 2 },
    ZAR: { symbol: 'R', decimals: 2 },
};

/**
 * Format in Indian numbering system (xx,xx,xxx.xx)
 */
function formatIndian(amount, decimals) {
    const neg = amount < 0;
    const abs = Math.abs(amount);
    const parts = abs.toFixed(decimals).split('.');
    let intPart = parts[0];
    const decPart = parts[1];

    if (intPart.length > 3) {
        const last3 = intPart.slice(-3);
        let rest = intPart.slice(0, -3);
        const groups = [];
        while (rest.length > 0) {
            groups.unshift(rest.slice(-2));
            rest = rest.slice(0, -2);
        }
        intPart = groups.join(',') + ',' + last3;
    }

    const formatted = decimals > 0 ? `${intPart}.${decPart}` : intPart;
    return neg ? `-${formatted}` : formatted;
}

/**
 * Format an amount in a specific currency with proper symbols and number formatting.
 * @param {number|null} amount
 * @param {string} currencyCode - e.g. 'USD', 'INR', 'EUR'
 * @returns {string}
 */
export function formatCurrency(amount, currencyCode = 'USD') {
    if (amount == null || isNaN(amount)) return '—';
    const fmt = CURRENCY_FORMATS[currencyCode] || { symbol: currencyCode + ' ', decimals: 2 };

    if (currencyCode === 'INR') {
        return `${fmt.symbol}${formatIndian(amount, fmt.decimals)}`;
    }

    return `${fmt.symbol}${Number(amount).toLocaleString('en-US', {
        minimumFractionDigits: fmt.decimals,
        maximumFractionDigits: fmt.decimals,
    })}`;
}

/**
 * Get the symbol for a currency code.
 */
export function getCurrencySymbol(currencyCode) {
    return (CURRENCY_FORMATS[currencyCode] || {}).symbol || currencyCode;
}

/**
 * Format market cap with abbreviations (T, B, M, K).
 */
export function formatMarketCap(cap, currencyCode = 'USD') {
    if (!cap) return '—';
    const sym = getCurrencySymbol(currencyCode);
    if (cap >= 1e12) return `${sym}${(cap / 1e12).toFixed(2)}T`;
    if (cap >= 1e9) return `${sym}${(cap / 1e9).toFixed(2)}B`;
    if (cap >= 1e6) return `${sym}${(cap / 1e6).toFixed(1)}M`;
    return `${sym}${cap.toLocaleString()}`;
}

export default { formatCurrency, getCurrencySymbol, formatMarketCap };
