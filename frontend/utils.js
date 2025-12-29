/**
 * Utility functions for the Agentic SQL Frontend
 */

export const UIUtils = {
    /**
     * Format a number as a percentage
     */
    formatPercent: (num) => {
        return `${Math.round(num * 100)}%`;
    },

    /**
     * Copy text to clipboard with feedback
     */
    copyToClipboard: async (text) => {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            console.error('Failed to copy: ', err);
            return false;
        }
    },

    /**
     * Debounce function for input handling
     */
    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};
