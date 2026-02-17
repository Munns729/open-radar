import React, { useState } from 'react';
import { useCurrency } from '@/context/CurrencyContext';
import { Calendar, ChevronDown } from 'lucide-react';

export default function CurrencySelector() {
    const { currency, date, updateSettings, loading } = useCurrency();
    const [isOpen, setIsOpen] = useState(false);

    const handleCurrencyChange = (newCurrency) => {
        updateSettings(newCurrency, date);
        setIsOpen(false);
    };

    const handleDateChange = (e) => {
        const newDate = e.target.value;
        updateSettings(currency, newDate);
    };

    const currencies = [
        { code: 'GBP', symbol: '£', label: 'British Pound' },
        { code: 'USD', symbol: '$', label: 'US Dollar' },
        { code: 'EUR', symbol: '€', label: 'Euro' },
    ];

    const currentCurrency = currencies.find(c => c.code === currency) || currencies[0];

    return (
        <div className="flex items-center gap-2 bg-surface-hover rounded-lg p-1 border border-border-subtle">
            {/* Currency Dropdown */}
            <div className="relative">
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    className="flex items-center gap-2 px-2 py-1 hover:bg-surface rounded text-sm font-medium text-text-pri transition-colors"
                >
                    <span>{currentCurrency.symbol} {currentCurrency.code}</span>
                    <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                </button>

                {isOpen && (
                    <div className="absolute top-full left-0 mt-1 w-32 bg-surface border border-border-subtle rounded-lg shadow-lg py-1 z-50">
                        {currencies.map((c) => (
                            <button
                                key={c.code}
                                onClick={() => handleCurrencyChange(c.code)}
                                className={`w-full text-left px-3 py-2 text-sm hover:bg-surface-hover transition-colors ${currency === c.code ? 'text-primary font-medium' : 'text-text-sec'
                                    }`}
                            >
                                {c.symbol} {c.code}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            <div className="w-px h-4 bg-border-subtle mx-1" />

            {/* Date Picker */}
            <div className="relative flex items-center">
                <Calendar className="w-4 h-4 text-text-sec absolute left-2 pointer-events-none" />
                <input
                    type="date"
                    value={date || ''}
                    onChange={handleDateChange}
                    className="pl-8 pr-2 py-1 bg-transparent text-sm text-text-pri focus:outline-none focus:ring-1 focus:ring-primary rounded cursor-pointer w-32"
                />
            </div>

            {loading && (
                <div className="w-2 h-2 rounded-full bg-primary animate-pulse mr-2" />
            )}
        </div>
    );
}
