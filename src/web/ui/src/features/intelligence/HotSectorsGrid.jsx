import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { TrendingUp, Flame, ArrowUpRight, ArrowDownRight, Activity } from 'lucide-react';
import { motion } from 'framer-motion';

export default function HotSectorsGrid() {
    const [sectors, setSectors] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                const res = await fetch('/api/intelligence/hot-sectors?limit=8');
                const json = await res.json();
                setSectors(json);
            } catch (error) {
                console.error("Failed to fetch hot sectors", error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const formatGBP = (value) => {
        if (!value) return '-';
        if (value >= 1000000000) return `£${(value / 1000000000).toFixed(1)}B`;
        if (value >= 1000000) return `£${(value / 1000000).toFixed(0)}M`;
        return `£${value.toLocaleString()}`;
    };

    const getHeatColor = (score) => {
        if (score >= 75) return 'from-orange-500/20 to-red-500/20 border-orange-500/50';
        if (score >= 50) return 'from-amber-500/20 to-orange-500/20 border-amber-500/50';
        if (score >= 25) return 'from-yellow-500/20 to-amber-500/20 border-yellow-500/50';
        return 'from-slate-700/20 to-slate-600/20 border-slate-500/50';
    };

    const getGrowthIcon = (growth) => {
        if (growth > 0) {
            return <ArrowUpRight className="h-4 w-4 text-green-400" />;
        } else if (growth < 0) {
            return <ArrowDownRight className="h-4 w-4 text-red-400" />;
        }
        return null;
    };

    return (
        <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl">
            <CardHeader>
                <CardTitle className="text-xl flex items-center gap-2">
                    <Flame className="h-5 w-5 text-orange-400" />
                    Hot Sectors
                </CardTitle>
                <CardDescription>
                    Sectors with rising deal activity and valuation multiples.
                </CardDescription>
            </CardHeader>
            <CardContent>
                {loading ? (
                    <div className="flex items-center justify-center h-48 text-muted-foreground">
                        Loading sector data...
                    </div>
                ) : sectors.length === 0 ? (
                    <div className="flex items-center justify-center h-48 text-muted-foreground">
                        No sector data available.
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        {sectors.map((sector, idx) => (
                            <motion.div
                                key={sector.sector}
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: idx * 0.05 }}
                                className={`relative rounded-xl p-4 border bg-gradient-to-br ${getHeatColor(sector.heat_score)} overflow-hidden`}
                            >
                                {/* Hot Badge */}
                                {sector.is_hot && (
                                    <div className="absolute top-2 right-2">
                                        <div className="flex items-center gap-1 bg-orange-500/30 text-orange-300 text-xs px-2 py-0.5 rounded-full">
                                            <Flame className="h-3 w-3" />
                                            HOT
                                        </div>
                                    </div>
                                )}

                                {/* Sector Name */}
                                <h3 className="font-semibold text-white mb-3">{sector.sector}</h3>

                                {/* Stats Grid */}
                                <div className="space-y-3">
                                    {/* Deal Count */}
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs text-muted-foreground">Deals</span>
                                        <div className="flex items-center gap-1">
                                            <span className="text-sm font-medium text-white">{sector.deal_count}</span>
                                            {getGrowthIcon(sector.deal_growth_pct)}
                                            {sector.deal_growth_pct !== 0 && (
                                                <span className={`text-xs ${sector.deal_growth_pct > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                    {sector.deal_growth_pct > 0 ? '+' : ''}{sector.deal_growth_pct}%
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Total Value */}
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs text-muted-foreground">Volume</span>
                                        <span className="text-sm font-medium text-emerald-400">
                                            {formatGBP(sector.total_value_gbp)}
                                        </span>
                                    </div>

                                    {/* Average Multiple */}
                                    {sector.avg_multiple && (
                                        <div className="flex items-center justify-between">
                                            <span className="text-xs text-muted-foreground">Avg Multiple</span>
                                            <div className="flex items-center gap-1">
                                                <span className="text-sm font-medium text-indigo-400">
                                                    {sector.avg_multiple}x
                                                </span>
                                                {sector.multiple_change_pct !== 0 && (
                                                    <span className={`text-xs ${sector.multiple_change_pct > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                        {sector.multiple_change_pct > 0 ? '+' : ''}{sector.multiple_change_pct}%
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    )}

                                    {/* Heat Score Bar */}
                                    <div className="mt-2">
                                        <div className="flex items-center justify-between text-xs mb-1">
                                            <span className="text-muted-foreground">Heat Score</span>
                                            <span className="text-amber-400 font-medium">{sector.heat_score}</span>
                                        </div>
                                        <div className="h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full transition-all duration-500"
                                                style={{ width: `${Math.min(sector.heat_score, 100)}%` }}
                                            />
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
