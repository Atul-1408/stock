import axios from 'axios';

// Base URL configuration: prefers VITE_API_BASE_URL if set, falls back to relative '/api'
const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api';
const baseURL = rawBaseUrl.endsWith('/') ? rawBaseUrl.slice(0, -1) : rawBaseUrl;

const api = axios.create({
    baseURL,
    timeout: 15000, // 15-second timeout to avoid hung connections
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor: attach sanitized JWT Bearer token
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        const isValidToken = token && token !== 'undefined' && token !== 'null' && token.trim().length > 0;
        if (isValidToken) {
            config.headers.Authorization = `Bearer ${token.trim()}`;
        } else {
            localStorage.removeItem('token');
            delete config.headers.Authorization;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response interceptor: structured error handling for 401, 403, 404, 422, 429, 500
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (!error.response) {
            // Network failure or timeout
            if (error.code === 'ECONNABORTED' || error.message?.toLowerCase().includes('timeout')) {
                error.userMessage = 'Request timed out. The server took too long to respond.';
            } else {
                error.userMessage = 'Network connection failed. Please verify the backend service is running.';
            }
            return Promise.reject(error);
        }

        const status = error.response.status;
        const resData = error.response.data || {};
        const url = error.config?.url || '';

        const isAuthEndpoint =
            url.includes('/auth/login') ||
            url.includes('/auth/otp') ||
            url.includes('/auth/google') ||
            url.includes('/auth/signup');

        const isAuthPage =
            typeof window !== 'undefined' &&
            (window.location.pathname === '/login' || window.location.pathname === '/signup');

        // Extract clean error message without exposing secrets
        let friendlyMessage =
            resData.message ||
            resData.error ||
            resData.msg ||
            error.message ||
            'An unexpected error occurred.';

        // 401: Unauthorized / Token Expired
        if (status === 401) {
            friendlyMessage = resData.message || 'Session expired. Please log in again.';
            if (!isAuthEndpoint && !isAuthPage) {
                localStorage.removeItem('token');
                localStorage.removeItem('user_id');
                window.location.href = '/login';
            }
        }

        // 422: Check if unprocessable entity is a malformed JWT or regular validation error
        else if (status === 422) {
            const rawMsg = String(friendlyMessage).toLowerCase();
            const isJwtError =
                rawMsg.includes('token') ||
                rawMsg.includes('signature') ||
                rawMsg.includes('segment') ||
                rawMsg.includes('jwt');

            if (isJwtError && !isAuthEndpoint && !isAuthPage) {
                friendlyMessage = 'Session signature invalid. Please log in again.';
                localStorage.removeItem('token');
                localStorage.removeItem('user_id');
                window.location.href = '/login';
            }
        }

        // 403: Forbidden / Permissions
        else if (status === 403) {
            friendlyMessage = resData.message || 'Access restricted. You do not have permission for this resource.';
        }

        // 404: Not Found
        else if (status === 404) {
            friendlyMessage = resData.message || 'The requested financial resource or endpoint was not found.';
        }

        // 429: Rate Limit
        else if (status === 429) {
            friendlyMessage = resData.message || 'Rate limit reached. Please wait a moment before sending more requests.';
        }

        // 500: Server Error
        else if (status >= 500) {
            friendlyMessage = resData.message || 'Backend service error. Please try again shortly.';
        }

        error.userMessage = friendlyMessage;
        return Promise.reject(error);
    }
);

export default api;
