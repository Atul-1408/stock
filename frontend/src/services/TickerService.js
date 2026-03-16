/**
 * Centralized Ticker Data Service
 * 
 * Prevents duplicate API requests by caching and batching ticker data requests.
 * All components should use this service instead of making direct API calls.
 */

import api from '../utils/api';

class TickerService {
    constructor() {
        this.cache = new Map(); // Cache for ticker data
        this.pendingRequests = new Map(); // Track ongoing requests
        this.subscribers = new Map(); // Component subscribers for updates
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes cache timeout
        this.refreshInterval = null;
    }

    /**
     * Fetch ticker data with caching and request deduplication
     * @param {string[]} tickers - Array of ticker symbols
     * @param {boolean} forceRefresh - Bypass cache if true
     * @returns {Promise<Object[]>} Array of ticker data
     */
    async fetchTickers(tickers, forceRefresh = false) {
        // Create cache key from sorted tickers
        const cacheKey = [...tickers].sort().join(',');
        
        // Return cached data if available and not expired
        if (!forceRefresh && this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                return cached.data;
            }
        }

        // Return pending request if one exists
        if (this.pendingRequests.has(cacheKey)) {
            return this.pendingRequests.get(cacheKey);
        }

        // Create new request
        const requestPromise = this._makeApiRequest(tickers, cacheKey);
        this.pendingRequests.set(cacheKey, requestPromise);

        try {
            const result = await requestPromise;
            // Cache the result
            this.cache.set(cacheKey, {
                data: result,
                timestamp: Date.now()
            });
            return result;
        } finally {
            // Clean up pending request
            this.pendingRequests.delete(cacheKey);
        }
    }

    /**
     * Make the actual API request with rate limiting
     * @param {string[]} tickers - Array of ticker symbols
     * @param {string} cacheKey - Cache key for this request
     * @returns {Promise<Object[]>} Array of ticker data
     */
    async _makeApiRequest(tickers, cacheKey) {
        // Implement rate limiting - max 10 tickers per request
        const batchSize = 10;
        const batches = [];
        
        for (let i = 0; i < tickers.length; i += batchSize) {
            batches.push(tickers.slice(i, i + batchSize));
        }

        const results = [];
        
        // Process batches sequentially to avoid rate limiting
        for (const batch of batches) {
            try {
                const response = await api.get(`/ticker-tape?tickers=${batch.join(',')}`);
                if (response.data?.tickers) {
                    results.push(...response.data.tickers);
                }
                // Add small delay between batches
                if (batches.length > 1) {
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
            } catch (error) {
                console.warn(`Failed to fetch batch:`, error);
                // Add null data for failed tickers
                results.push(...batch.map(ticker => ({
                    ticker,
                    price: null,
                    change: null,
                    changePct: null
                })));
            }
        }

        return results;
    }

    /**
     * Subscribe to ticker updates
     * @param {string} componentId - Unique component identifier
     * @param {Function} callback - Callback function to receive updates
     * @param {string[]} tickers - Tickers to monitor
     */
    subscribe(componentId, callback, tickers) {
        this.subscribers.set(componentId, { callback, tickers });

        // Immediate refresh for this subscriber (deduped + cached)
        this.fetchTickers(tickers)
            .then((data) => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error notifying subscriber ${componentId}:`, error);
                }
            })
            .catch(() => { });
        
        // Start refresh interval if not already running
        if (!this.refreshInterval) {
            this.startAutoRefresh();
        }
    }

    /**
     * Unsubscribe from ticker updates
     * @param {string} componentId - Component identifier to remove
     */
    unsubscribe(componentId) {
        this.subscribers.delete(componentId);
        
        // Stop refresh if no subscribers
        if (this.subscribers.size === 0) {
            this.stopAutoRefresh();
        }
    }

    /**
     * Start automatic refresh of ticker data
     */
    startAutoRefresh() {
        if (this.refreshInterval) return;
        
        this.refreshInterval = setInterval(() => {
            this._refreshAllSubscribers();
        }, 15000); // Refresh every 15 seconds
    }

    /**
     * Stop automatic refresh
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    /**
     * Refresh data for all subscribers
     */
    async _refreshAllSubscribers() {
        // Collect all unique tickers from subscribers
        const allTickers = new Set();
        for (const { tickers } of this.subscribers.values()) {
            tickers.forEach(ticker => allTickers.add(ticker));
        }

        if (allTickers.size === 0) return;

        try {
            const tickerArray = Array.from(allTickers);
            const freshData = await this.fetchTickers(tickerArray, true);
            
            // Notify all subscribers with relevant data
            const dataMap = new Map(freshData.map(item => [item.ticker, item]));
            
            for (const [componentId, { callback, tickers }] of this.subscribers) {
                const componentData = tickers.map(ticker => 
                    dataMap.get(ticker) || { ticker, price: null, change: null, changePct: null }
                );
                try {
                    callback(componentData);
                } catch (error) {
                    console.error(`Error notifying subscriber ${componentId}:`, error);
                }
            }
        } catch (error) {
            console.error('Failed to refresh ticker data:', error);
        }
    }

    /**
     * Clear all cached data
     */
    clearCache() {
        this.cache.clear();
    }

    /**
     * Get cache statistics
     */
    getCacheStats() {
        return {
            cachedItems: this.cache.size,
            pendingRequests: this.pendingRequests.size,
            subscribers: this.subscribers.size
        };
    }
}

// Export singleton instance
export const tickerService = new TickerService();

// Export convenience functions
export const fetchTickers = (tickers, forceRefresh) => 
    tickerService.fetchTickers(tickers, forceRefresh);

export const subscribeToTickers = (componentId, callback, tickers) =>
    tickerService.subscribe(componentId, callback, tickers);

export const unsubscribeFromTickers = (componentId) =>
    tickerService.unsubscribe(componentId);