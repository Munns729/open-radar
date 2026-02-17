import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Flame, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function MarketTrends() {
    const [trends, setTrends] = useState([]);
    const [hotSectors, setHotSectors] = useState([]);
    const [loading, setLoading] = useState(true);
    const [sector, setSector] = useState('');

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                const [trendRes, hotRes] = await Promise.all([
                    fetch(`/api/intelligence/market-trends?months=12${sector ? `&sector=${sector}` : ''}`),
                    fetch('/api/intelligence/hot-sectors')
                ]);

                if (trendRes.ok) {
                    const trendData = await trendRes.json();
                    setTrends(trendData);
                }

                if (hotRes.ok) {
                    const hotData = await hotRes.json();
                    setHotSectors(hotData);
                }
            } catch (error) {
                console.error('Failed to fetch market trends:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [sector]);

    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-surface border border-border-subtle p-3 rounded-lg shadow-lg">
                    <p className="font-medium text-text-pri mb-2">{label}</p>
                    {payload.map((entry, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-sm text-text-sec">
                            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
                            <span>{entry.name}:</span>
                            <span className="font-mono font-medium text-text-pri">{entry.value.toFixed(1)}x</span>
                        </div>
                    ))}
                </div>
            );
        }
        return null;
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-end">
                <select
                    className="h-9 rounded-md border border-border-subtle bg-surface-alt px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                    value={sector}
                    onChange={(e) => setSector(e.target.value)}
                >
                    <option value="">All Sectors</option>
                    <option value="TMT">TMT</option>
                    <option value="Healthcare">Healthcare</option>
                    <option value="Industrial">Industrial</option>
                    <option value="Consumer">Consumer</option>
                </select>
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="bg-surface border-border-subtle">
                    <CardHeader>
                        <CardTitle className="text-lg">Median EV/EBITDA Multiples</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="h-[300px] w-full">
                            {loading ? (
                                <div className="h-full flex items-center justify-center text-text-sec">Loading chart...</div>
                            ) : trends.length === 0 ? (
                                <div className="h-full flex items-center justify-center text-text-sec">No data available</div>
                            ) : (
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={trends}>
                                        <defs>
                                            <linearGradient id="colorEbitda" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.3} />
                                                <stop offset="95%" stopColor="var(--primary)" stopOpacity={0} />
                                            </linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                                        <XAxis
                                            dataKey="time_period"
                                            stroke="var(--text-ter)"
                                            fontSize={12}
                                            tickLine={false}
                                            axisLine={false}
                                        />
                                        <YAxis
                                            stroke="var(--text-ter)"
                                            fontSize={12}
                                            tickLine={false}
                                            axisLine={false}
                                            domain={['auto', 'auto']}
                                        />
                                        <Tooltip content={<CustomTooltip />} />
                                        <Area
                                            type="monotone"
                                            dataKey="median_ev_ebitda"
                                            name="EV/EBITDA"
                                            stroke="var(--primary)"
                                            fillOpacity={1}
                                            fill="url(#colorEbitda)"
                                            strokeWidth={2}
                                        />
                                    </AreaChart>
                                </ResponsiveContainer>
                            )}
                        </div>
                    </CardContent>
                </Card>

                <Card className="bg-surface border-border-subtle">
                    <CardHeader>
                        <CardTitle className="text-lg">Median EV/Revenue Multiples</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="h-[300px] w-full">
                            {loading ? (
                                <div className="h-full flex items-center justify-center text-text-sec">Loading chart...</div>
                            ) : trends.length === 0 ? (
                                <div className="h-full flex items-center justify-center text-text-sec">No data available</div>
                            ) : (
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={trends}>
                                        <defs>
                                            <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="var(--success)" stopOpacity={0.3} />
                                                <stop offset="95%" stopColor="var(--success)" stopOpacity={0} />
                                            </linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                                        <XAxis
                                            dataKey="time_period"
                                            stroke="var(--text-ter)"
                                            fontSize={12}
                                            tickLine={false}
                                            axisLine={false}
                                        />
                                        <YAxis
                                            stroke="var(--text-ter)"
                                            fontSize={12}
                                            tickLine={false}
                                            axisLine={false}
                                            domain={['auto', 'auto']}
                                        />
                                        <Tooltip content={<CustomTooltip />} />
                                        <Area
                                            type="monotone"
                                            dataKey="median_ev_revenue"
                                            name="EV/Revenue"
                                            stroke="var(--success)"
                                            fillOpacity={1}
                                            fill="url(#colorRev)"
                                            strokeWidth={2}
                                        />
                                    </AreaChart>
                                </ResponsiveContainer>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Hot Sectors API currently returns list of objects with sector, deal_count, trend_score */}
            <Card className="bg-surface border-border-subtle">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Flame className="h-5 w-5 text-orange-400" />
                        Hot Sectors (Last 6 Months)
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {loading && hotSectors.length === 0 ? (
                            <div className="col-span-3 text-center py-8 text-text-sec">Loading hot sectors...</div>
                        ) : hotSectors.map((item, idx) => (
                            <div key={idx} className="flex flex-col p-4 rounded-lg bg-surface-alt border border-border-subtle">
                                <div className="flex justify-between items-start mb-2">
                                    <h3 className="font-semibold text-text-pri">{item.sector}</h3>
                                    <Badge variant="outline" className={cn(
                                        "capitalize",
                                        item.trend_direction === 'up' ? "text-success border-success/20 bg-success/5" :
                                            item.trend_direction === 'down' ? "text-danger border-danger/20 bg-danger/5" :
                                                "text-text-sec border-border-subtle"
                                    )}>
                                        {item.trend_direction === 'up' ? <TrendingUp className="h-3 w-3 mr-1" /> :
                                            item.trend_direction === 'down' ? <TrendingDown className="h-3 w-3 mr-1" /> :
                                                <RefreshCw className="h-3 w-3 mr-1" />}
                                        {item.growth_rate}%
                                    </Badge>
                                </div>
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                    <div className="text-text-sec">Deal Count</div>
                                    <div className="text-text-pri font-medium text-right">{item.deal_count}</div>
                                    <div className="text-text-sec">Avg Multiple</div>
                                    <div className="text-text-pri font-medium text-right">{item.avg_multiple?.toFixed(1)}x</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
