import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X, Building2, Users, Briefcase } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

export default function GlobalSearch() {
    const [isOpen, setIsOpen] = useState(false);
    const [query, setQuery] = useState('');
    const [results, setResults] = useState({ companies: [], contacts: [], deals: [] });
    const [loading, setLoading] = useState(false);
    const inputRef = useRef(null);
    const navigate = useNavigate();

    // Keyboard shortcut: Cmd/Ctrl + K
    useEffect(() => {
        const handleKeyDown = (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                setIsOpen(true);
            }
            if (e.key === 'Escape') {
                setIsOpen(false);
            }
        };
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, []);

    // Focus input when opened
    useEffect(() => {
        if (isOpen && inputRef.current) {
            inputRef.current.focus();
        }
    }, [isOpen]);

    // Debounced search
    useEffect(() => {
        if (!query.trim()) {
            setResults({ companies: [], contacts: [], deals: [] });
            return;
        }

        const debounce = setTimeout(async () => {
            setLoading(true);
            try {
                const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
                if (res.ok) {
                    const data = await res.json();
                    setResults(data);
                }
            } catch (error) {
                console.error('Search failed:', error);
            } finally {
                setLoading(false);
            }
        }, 300);

        return () => clearTimeout(debounce);
    }, [query]);

    const handleResultClick = (type, item) => {
        setIsOpen(false);
        setQuery('');
        switch (type) {
            case 'company':
                navigate(`/universe?search=${encodeURIComponent(item.name)}`);
                break;
            case 'contact':
                navigate(`/relationships?id=${item.id}`);
                break;
            case 'deal':
                navigate(`/intelligence?deal=${item.id}`);
                break;
        }
    };

    const hasResults = results.companies.length > 0 || results.contacts.length > 0 || results.deals.length > 0;

    return (
        <>
            {/* Search Trigger Button */}
            <button
                onClick={() => setIsOpen(true)}
                className="flex items-center gap-2 px-3 py-2 bg-surface-alt border border-border-subtle rounded-lg text-text-sec hover:text-text-pri hover:bg-surface-hover transition-colors"
            >
                <Search className="h-4 w-4" />
                <span className="text-sm hidden sm:inline">Search...</span>
                <kbd className="hidden md:inline-flex h-5 items-center gap-1 rounded border border-border-subtle bg-surface px-1.5 font-mono text-[10px] font-medium text-text-ter">
                    <span className="text-xs">⌘</span>K
                </kbd>
            </button>

            {/* Search Modal */}
            <AnimatePresence>
                {isOpen && (
                    <>
                        {/* Backdrop */}
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
                            onClick={() => setIsOpen(false)}
                        />

                        {/* Search Panel */}
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95, y: -20 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95, y: -20 }}
                            transition={{ duration: 0.15 }}
                            className="fixed top-[15%] left-1/2 -translate-x-1/2 w-full max-w-xl z-50"
                        >
                            <div className="bg-surface border border-border rounded-xl shadow-2xl overflow-hidden">
                                {/* Search Input */}
                                <div className="flex items-center gap-3 p-4 border-b border-border-subtle">
                                    <Search className="h-5 w-5 text-text-ter" />
                                    <input
                                        ref={inputRef}
                                        type="text"
                                        value={query}
                                        onChange={(e) => setQuery(e.target.value)}
                                        placeholder="Search companies, contacts, deals..."
                                        className="flex-1 bg-transparent text-text-pri placeholder-text-ter outline-none text-base"
                                    />
                                    {query && (
                                        <button
                                            onClick={() => setQuery('')}
                                            className="text-text-sec hover:text-text-pri"
                                        >
                                            <X className="h-4 w-4" />
                                        </button>
                                    )}
                                </div>

                                {/* Results */}
                                <div className="max-h-[400px] overflow-y-auto">
                                    {loading ? (
                                        <div className="p-8 text-center text-text-sec">
                                            <div className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                                            <p className="mt-2 text-sm">Searching...</p>
                                        </div>
                                    ) : !query ? (
                                        <div className="p-8 text-center text-text-sec">
                                            <p className="text-sm">Start typing to search across RADAR</p>
                                        </div>
                                    ) : !hasResults ? (
                                        <div className="p-8 text-center text-text-sec">
                                            <p className="text-sm">No results found for "{query}"</p>
                                        </div>
                                    ) : (
                                        <div className="p-2">
                                            {/* Companies */}
                                            {results.companies.length > 0 && (
                                                <div className="mb-2">
                                                    <div className="px-3 py-2 text-xs font-semibold text-text-ter uppercase tracking-wider">
                                                        Companies
                                                    </div>
                                                    {results.companies.slice(0, 5).map((item) => (
                                                        <button
                                                            key={item.id}
                                                            onClick={() => handleResultClick('company', item)}
                                                            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-surface-hover text-left transition-colors"
                                                        >
                                                            <Building2 className="h-4 w-4 text-primary" />
                                                            <div>
                                                                <div className="text-sm font-medium text-text-pri">{item.name}</div>
                                                                <div className="text-xs text-text-sec">{item.sector}</div>
                                                            </div>
                                                        </button>
                                                    ))}
                                                </div>
                                            )}

                                            {/* Contacts */}
                                            {results.contacts.length > 0 && (
                                                <div className="mb-2">
                                                    <div className="px-3 py-2 text-xs font-semibold text-text-ter uppercase tracking-wider">
                                                        Contacts
                                                    </div>
                                                    {results.contacts.slice(0, 5).map((item) => (
                                                        <button
                                                            key={item.id}
                                                            onClick={() => handleResultClick('contact', item)}
                                                            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-surface-hover text-left transition-colors"
                                                        >
                                                            <Users className="h-4 w-4 text-success" />
                                                            <div>
                                                                <div className="text-sm font-medium text-text-pri">{item.name}</div>
                                                                <div className="text-xs text-text-sec">{item.company || item.role}</div>
                                                            </div>
                                                        </button>
                                                    ))}
                                                </div>
                                            )}

                                            {/* Deals */}
                                            {results.deals.length > 0 && (
                                                <div>
                                                    <div className="px-3 py-2 text-xs font-semibold text-text-ter uppercase tracking-wider">
                                                        Deals
                                                    </div>
                                                    {results.deals.slice(0, 5).map((item) => (
                                                        <button
                                                            key={item.id}
                                                            onClick={() => handleResultClick('deal', item)}
                                                            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-surface-hover text-left transition-colors"
                                                        >
                                                            <Briefcase className="h-4 w-4 text-warning" />
                                                            <div>
                                                                <div className="text-sm font-medium text-text-pri">{item.name}</div>
                                                                <div className="text-xs text-text-sec">{item.type}</div>
                                                            </div>
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>

                                {/* Footer */}
                                <div className="flex items-center justify-between px-4 py-2 border-t border-border-subtle bg-surface-alt text-xs text-text-ter">
                                    <span>Press <kbd className="px-1 py-0.5 bg-surface border border-border-subtle rounded">ESC</kbd> to close</span>
                                    <span>↑↓ to navigate, ↵ to select</span>
                                </div>
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </>
    );
}
