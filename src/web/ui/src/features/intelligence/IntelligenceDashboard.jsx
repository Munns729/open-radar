import React, { useState } from 'react';
import DealTable from './DealTable';
import MarketTrends from './MarketTrends';
import ValuationCalculator from './ValuationCalculator';
import { LayoutDashboard, TrendingUp, Calculator } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function IntelligenceDashboard() {
    const [activeTab, setActiveTab] = useState('deals');

    const TABS = [
        { id: 'deals', label: 'Deal Transactions', icon: LayoutDashboard },
        { id: 'trends', label: 'Market Trends', icon: TrendingUp },
        { id: 'valuation', label: 'Valuation Tool', icon: Calculator },
    ];

    return (
        <div className="space-y-6">
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-text-pri">Deal Intelligence</h1>
                    <p className="text-text-sec text-sm mt-1">
                        Track PE deal activity, pricing benchmarks, and valuation trends in real-time.
                    </p>
                </div>

                <div className="flex p-1 bg-surface-alt rounded-lg border border-border-subtle">
                    {TABS.map((tab) => {
                        const Icon = tab.icon;
                        const isActive = activeTab === tab.id;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={cn(
                                    "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all",
                                    isActive
                                        ? "bg-surface shadow text-text-pri"
                                        : "text-text-sec hover:text-text-pri hover:bg-surface-hover"
                                )}
                            >
                                <Icon className="h-4 w-4" />
                                {tab.label}
                            </button>
                        );
                    })}
                </div>
            </header>

            <div className="min-h-[500px]">
                {activeTab === 'deals' && <DealTable />}
                {activeTab === 'trends' && <MarketTrends />}
                {activeTab === 'valuation' && <ValuationCalculator />}
            </div>
        </div>
    );
}
