import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { TrendingUp, Calendar, Filter } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function MarketTrendsChart() {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [sector, setSector] = useState('');
    const [months, setMonths] = useState(24);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                let url = `/api/intelligence/market-trends?months=${months}`;
                if (sector) url += `&sector=${sector}`;

                const res = await fetch(url);
                const json = await res.json();

                // Process data for chart
                const processedData = json.map(item => ({
                    period: item.time_period,
                    evEbitda: item.median_ev_ebitda || item.avg_ev_ebitda,
                    evRevenue: item.median_ev_revenue || item.avg_ev_revenue,
                    dealCount: item.deal_count,
                    totalValue: item.total_value_gbp / 1000000, // Convert to millions
                    sector: item.sector
                }));

                setData(processedData);
            } catch (error) {
                console.error("Failed to fetch market trends", error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [sector, months]);

    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-slate-900 border border-border/50 rounded-lg p-3 shadow-xl">
                    <p className="text-sm font-medium text-white mb-2">{label}</p>
                    {payload.map((entry, index) => (
                        <p key={index} className="text-xs" style={{ color: entry.color }}>
                            {entry.name}: {entry.value?.toFixed(1)}{entry.name.includes('Multiple') ? 'x' : ''}
                        </p>
                    ))}
                </div>
            );
        }
        return null;
    };

    return (
        <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl">
            <CardHeader>
                <div className="flex items-start justify-between">
                    <div>
                        <CardTitle className="text-xl flex items-center gap-2">
                            <TrendingUp className="h-5 w-5 text-indigo-400" />
                            Market Valuation Trends
                        </CardTitle>
                        <CardDescription>
                            Median valuation multiples over time by sector.
                        </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                        <select
                            className="h-9 rounded-lg border border-input bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
                            value={sector}
                            onChange={(e) => setSector(e.target.value)}
                        >
                            <option value="">All Sectors</option>
                            <option value="Technology">Technology</option>
                            <option value="Healthcare">Healthcare</option>
                            <option value="Industrial">Industrial</option>
                            <option value="Financial Services">Financial Services</option>
                            <option value="Consumer">Consumer</option>
                        </select>
                        <select
                            className="h-9 rounded-lg border border-input bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
                            value={months}
                            onChange={(e) => setMonths(Number(e.target.value))}
                        >
                            <option value={12}>1 Year</option>
                            <option value={24}>2 Years</option>
                            <option value={36}>3 Years</option>
                            <option value={60}>5 Years</option>
                        </select>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                {loading ? (
                    <div className="flex items-center justify-center h-80 text-muted-foreground">
                        Loading trends...
                    </div>
                ) : data.length === 0 ? (
                    <div className="flex items-center justify-center h-80 text-muted-foreground">
                        No trend data available for the selected criteria.
                    </div>
                ) : (
                    <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                <XAxis
                                    dataKey="period"
                                    stroke="#94a3b8"
                                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                                />
                                <YAxis
                                    yAxisId="left"
                                    stroke="#94a3b8"
                                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                                    label={{ value: 'Multiple', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
                                />
                                <YAxis
                                    yAxisId="right"
                                    orientation="right"
                                    stroke="#94a3b8"
                                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                                    label={{ value: 'Deal Count', angle: 90, position: 'insideRight', fill: '#94a3b8' }}
                                />
                                <Tooltip content={<CustomTooltip />} />
                                <Legend
                                    wrapperStyle={{ paddingTop: '20px' }}
                                    formatter={(value) => <span className="text-slate-300">{value}</span>}
                                />
                                <Line
                                    yAxisId="left"
                                    type="monotone"
                                    dataKey="evEbitda"
                                    name="EV/EBITDA Multiple"
                                    stroke="#818cf8"
                                    strokeWidth={2}
                                    dot={{ fill: '#818cf8', strokeWidth: 2, r: 4 }}
                                    activeDot={{ r: 6 }}
                                />
                                <Line
                                    yAxisId="left"
                                    type="monotone"
                                    dataKey="evRevenue"
                                    name="EV/Revenue Multiple"
                                    stroke="#34d399"
                                    strokeWidth={2}
                                    dot={{ fill: '#34d399', strokeWidth: 2, r: 4 }}
                                    activeDot={{ r: 6 }}
                                />
                                <Line
                                    yAxisId="right"
                                    type="monotone"
                                    dataKey="dealCount"
                                    name="Deal Count"
                                    stroke="#fbbf24"
                                    strokeWidth={2}
                                    strokeDasharray="5 5"
                                    dot={{ fill: '#fbbf24', strokeWidth: 2, r: 3 }}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                )}

                {/* Summary Stats */}
                {data.length > 0 && (
                    <div className="mt-6 grid grid-cols-3 gap-4">
                        <div className="bg-slate-900/50 rounded-lg p-4 border border-border/30 text-center">
                            <div className="text-xs text-muted-foreground uppercase tracking-wider">Avg EV/EBITDA</div>
                            <div className="text-xl font-bold text-indigo-400 mt-1">
                                {(data.reduce((acc, d) => acc + (d.evEbitda || 0), 0) / data.filter(d => d.evEbitda).length).toFixed(1)}x
                            </div>
                        </div>
                        <div className="bg-slate-900/50 rounded-lg p-4 border border-border/30 text-center">
                            <div className="text-xs text-muted-foreground uppercase tracking-wider">Avg EV/Revenue</div>
                            <div className="text-xl font-bold text-emerald-400 mt-1">
                                {(data.reduce((acc, d) => acc + (d.evRevenue || 0), 0) / data.filter(d => d.evRevenue).length).toFixed(1)}x
                            </div>
                        </div>
                        <div className="bg-slate-900/50 rounded-lg p-4 border border-border/30 text-center">
                            <div className="text-xs text-muted-foreground uppercase tracking-wider">Total Deals</div>
                            <div className="text-xl font-bold text-amber-400 mt-1">
                                {data.reduce((acc, d) => acc + (d.dealCount || 0), 0)}
                            </div>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
