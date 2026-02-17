import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '@/lib/api';

const CurrencyContext = createContext();

export function CurrencyProvider({ children }) {
    const [currency, setCurrency] = useState('GBP');
    const [date, setDate] = useState(null); // String YYYY-MM-DD
    const [rates, setRates] = useState({ GBP: 1, EUR: 1.17, USD: 1.27 });
    const [loading, setLoading] = useState(true);

    // Initial fetch
    useEffect(() => {
        fetchConfig();
    }, []);

    const fetchConfig = async () => {
        try {
            const config = await api.get('/config/currency');
            setCurrency(config.preferred_currency);
            setDate(config.currency_date); // Will be resolved date from backend
            setRates(config.rates);
        } catch (error) {
            console.error("Failed to load currency config:", error);
        } finally {
            setLoading(false);
        }
    };

    const updateSettings = async (newCurrency, newDate) => {
        setLoading(true);
        // Optimistic update
        setCurrency(newCurrency);
        setDate(newDate);

        try {
            await api.post('/config/currency', {
                preferred_currency: newCurrency,
                currency_date: newDate
            });
            // Re-fetch to get new rates for the date
            await fetchConfig();
        } catch (error) {
            console.error("Failed to update currency settings:", error);
            // Revert on failure (could improve this)
        } finally {
            setLoading(false);
        }
    };

    const convert = (amount, fromCurrency = 'GBP') => {
        if (!amount) return 0;

        // Convert to Base (GBP)
        let inBase = amount;
        if (fromCurrency !== 'GBP') {
            const rate = rates[fromCurrency] || 1;
            inBase = amount / rate;
        }

        // Convert to Target
        const targetRate = rates[currency] || 1;
        return inBase * targetRate;
    };

    const format = (amount, fromCurrency = 'GBP') => {
        const value = convert(amount, fromCurrency);
        return new Intl.NumberFormat('en-GB', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(value);
    };

    return (
        <CurrencyContext.Provider value={{
            currency,
            date,
            rates,
            loading,
            updateSettings,
            convert,
            format
        }}>
            {children}
        </CurrencyContext.Provider>
    );
}

export function useCurrency() {
    return useContext(CurrencyContext);
}
