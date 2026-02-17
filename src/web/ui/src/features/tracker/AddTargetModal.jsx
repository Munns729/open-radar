import React, { useState } from 'react';
import api from '@/lib/api';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Search, Loader2, Check, Filter, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function AddTargetModal({ isOpen, onClose, onSuccess }) {
    const [step, setStep] = useState(1); // 1: Search, 2: Configure
    const [searchQuery, setSearchQuery] = useState('');
    const [filters, setFilters] = useState({
        tier: '',
        sector: '',
        country: '',
        minMoat: ''
    });
    const [showFilters, setShowFilters] = useState(false);
    const [searchResults, setSearchResults] = useState([]);
    const [selectedIds, setSelectedIds] = useState([]);
    const [searching, setSearching] = useState(false);

    const [config, setConfig] = useState({
        priority: 'medium',
        tags: ''
    });
    const [submitting, setSubmitting] = useState(false);

    const handleSearch = async () => {
        setSearching(true);
        try {
            const data = await api.getCompanies({
                limit: 50,
                search: searchQuery || undefined,
                tier: filters.tier || undefined,
                sector: filters.sector || undefined,
                country: filters.country || undefined,
                min_moat: filters.minMoat ? parseInt(filters.minMoat) : undefined
            });
            // PaginatedResponse unpacked data is { data: [...], total: ... }
            setSearchResults(data.data || data || []);
        } catch (error) {
            console.error("Search failed", error);
        } finally {
            setSearching(false);
        }
    };

    const toggleSelection = (id) => {
        setSelectedIds(prev =>
            prev.includes(id)
                ? prev.filter(i => i !== id)
                : [...prev, id]
        );
    };

    const handleContinue = () => {
        if (selectedIds.length === 0) return;
        setStep(2);
    };

    const handleSubmit = async () => {
        setSubmitting(true);
        try {
            await api.batchAddTargets({
                company_ids: selectedIds,
                priority: config.priority,
                tags: config.tags.split(',').map(t => t.trim()).filter(Boolean)
            });

            onSuccess();
            onClose();
        } catch (error) {
            console.error("Failed to add targets", error);
        } finally {
            setSubmitting(false);
        }
    };

    const resetSelection = () => {
        setSelectedIds([]);
        setStep(1);
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[600px] max-h-[90vh] flex flex-col">
                <DialogHeader>
                    <DialogTitle>{step === 1 ? 'Find Targets' : 'Configure Tracking'}</DialogTitle>
                    <DialogDescription>
                        {step === 1
                            ? 'Filter the Universe and select companies to track in bulk.'
                            : `Configuring tracking for ${selectedIds.length} selected companies.`}
                    </DialogDescription>
                </DialogHeader>

                {step === 1 ? (
                    <div className="space-y-4 py-4 overflow-hidden flex flex-col">
                        <div className="flex gap-2">
                            <div className="relative flex-1">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-ter" />
                                <Input
                                    className="pl-9"
                                    placeholder="Search by company name..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                                />
                            </div>
                            <Button
                                variant={showFilters ? "secondary" : "outline"}
                                onClick={() => setShowFilters(!showFilters)}
                            >
                                <Filter className="h-4 w-4 mr-2" />
                                Filters
                            </Button>
                            <Button onClick={handleSearch} disabled={searching}>
                                {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Search'}
                            </Button>
                        </div>

                        {showFilters && (
                            <div className="p-3 bg-surface-alt rounded-lg grid grid-cols-2 gap-3 border border-border-subtle animate-in fade-in slide-in-from-top-2">
                                <div className="space-y-1">
                                    <label className="text-xs font-semibold text-text-sec">Company Tier</label>
                                    <Select
                                        value={filters.tier}
                                        onChange={(e) => setFilters({ ...filters, tier: e.target.value })}
                                    >
                                        <option value="">All Tiers</option>
                                        <option value="1A">Tier 1A (£15-100M, High Moat)</option>
                                        <option value="1B">Tier 1B (£15-100M, Mod Moat)</option>
                                        <option value="2">Tier 2 (Watch)</option>
                                    </Select>
                                </div>
                                <div className="space-y-1">
                                    <label className="text-xs font-semibold text-text-sec">HQ Country (ISO)</label>
                                    <Input
                                        placeholder="e.g. UK, DE, FR"
                                        value={filters.country}
                                        onChange={(e) => setFilters({ ...filters, country: e.target.value.toUpperCase() })}
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-xs font-semibold text-text-sec">Sector</label>
                                    <Input
                                        placeholder="e.g. Software, FinTech"
                                        value={filters.sector}
                                        onChange={(e) => setFilters({ ...filters, sector: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-xs font-semibold text-text-sec">Min Moat Score</label>
                                    <Input
                                        type="number"
                                        placeholder="0-100"
                                        value={filters.minMoat}
                                        onChange={(e) => setFilters({ ...filters, minMoat: e.target.value })}
                                    />
                                </div>
                            </div>
                        )}

                        <div className="flex-1 overflow-y-auto min-h-0 space-y-2 pr-1">
                            {searchResults.map(company => (
                                <div
                                    key={company.id}
                                    onClick={() => toggleSelection(company.id)}
                                    className={cn(
                                        "p-3 rounded-lg border transition-all cursor-pointer flex justify-between items-center group",
                                        selectedIds.includes(company.id)
                                            ? "border-primary bg-primary/5 shadow-sm"
                                            : "border-border-subtle hover:border-text-ter bg-surface"
                                    )}
                                >
                                    <div className="flex-1 min-w-0 pr-4">
                                        <div className="flex items-center gap-2">
                                            <p className="font-semibold text-text-pri truncate">{company.name}</p>
                                            {company.tier && (
                                                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-accent/20 text-accent uppercase">
                                                    Tier {company.tier}
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-xs text-text-sec truncate mt-0.5">
                                            {company.sector} • {company.hq_country} • Moat: {company.moat_score}
                                        </p>
                                    </div>
                                    <div className={cn(
                                        "h-5 w-5 rounded border flex items-center justify-center transition-colors",
                                        selectedIds.includes(company.id)
                                            ? "bg-primary border-primary text-white"
                                            : "border-border-subtle group-hover:border-text-ter"
                                    )}>
                                        {selectedIds.includes(company.id) && <Check className="h-3 w-3" />}
                                    </div>
                                </div>
                            ))}
                            {searchResults.length === 0 && !searching && (
                                <div className="text-center py-10 opacity-50">
                                    <Search className="h-8 w-8 mx-auto mb-2" />
                                    <p className="text-sm">Search and filter to find companies</p>
                                </div>
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="space-y-4 py-4 animate-in fade-in scale-in-95">
                        <div className="p-3 bg-surface-alt rounded-lg border border-border-subtle flex items-center justify-between">
                            <span className="text-sm font-medium">{selectedIds.length} companies selected</span>
                            <Button variant="ghost" size="sm" onClick={resetSelection} className="h-7 text-xs">
                                Edit Selection
                            </Button>
                        </div>

                        <div className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Tracking Priority</label>
                                <Select
                                    value={config.priority}
                                    onChange={(e) => setConfig({ ...config, priority: e.target.value })}
                                >
                                    <option value="high">High - Daily Intelligence</option>
                                    <option value="medium">Medium - Weekly Pulse</option>
                                    <option value="low">Low - Monthly Review</option>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Workflow Tags</label>
                                <Input
                                    placeholder="e.g. High Moat, UK Focus, Series B"
                                    value={config.tags}
                                    onChange={(e) => setConfig({ ...config, tags: e.target.value })}
                                />
                                <p className="text-[10px] text-text-ter">Separate tags with commas</p>
                            </div>
                        </div>
                    </div>
                )}

                <DialogFooter className="border-t border-border-subtle pt-4 mt-2">
                    <Button variant="ghost" onClick={onClose}>Cancel</Button>
                    {step === 1 ? (
                        <Button
                            disabled={selectedIds.length === 0}
                            onClick={handleContinue}
                            className="w-32"
                        >
                            Continue ({selectedIds.length})
                        </Button>
                    ) : (
                        <Button onClick={handleSubmit} disabled={submitting} className="w-40">
                            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : `Track ${selectedIds.length} Targets`}
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
