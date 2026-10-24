/**
 * Centralized utility for Google Sign-In (GSI) initialization.
 * Ensures that google.accounts.id.initialize is called only once.
 */

const GOOGLE_CLIENT_ID = '1080262616416-ii4tln966156c7niafikjv6g1ifqnqfi.apps.googleusercontent.com';

let isInitialized = false;

export const initGSI = (callback) => {
    if (typeof window === 'undefined' || !window.google?.accounts?.id) {
        return false;
    }

    if (!isInitialized) {
        window.google.accounts.id.initialize({
            client_id: GOOGLE_CLIENT_ID,
            callback: callback,
        });
        isInitialized = true;
    }

    return true;
};

export const renderGSIButton = (element, options = {}) => {
    if (typeof window === 'undefined' || !window.google?.accounts?.id || !element) {
        return;
    }

    window.google.accounts.id.renderButton(element, {
        theme: 'filled_black',
        size: 'large',
        width: 380,
        shape: 'pill',
        text: 'continue_with',
        logo_alignment: 'center',
        ...options
    });
};
