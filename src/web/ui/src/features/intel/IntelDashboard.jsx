import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Newspaper, TrendingUp, FileText, Loader2 } from 'lucide-react';

const CATEGORY_COLORS = {
    fintech: 'bg-blue-500/20 text-blue-300',
    regulatory: 'bg-amber-500/20 text-amber-300',
    ai: 'bg-purple-500/20 text-purple-300',
    ma: 'bg-emerald-500/20 text-emerald-300'
};

const RELEVANCE_COLORS = {
    high: 'text-red-400',
    medium: 'text-amber-400',
    low: 'text-slate-400'
};

export default function IntelDashboard() {
    const [items, setItems] = useState([]);
    const [trends, setTrends] = useState([]);
    const [briefing, setBriefing] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchAllData();
    }, []);

    const fetchAllData = async () => {
        setLoading(true);
        try {
            const [itemsRes, trendsRes, briefingRes] = await Promise.all([
                fetch('/api/intel/items'),
                fetch('/api/intel/trends'),
                fetch('/api/intel/briefing/latest')
            ]);

            const itemsData = await itemsRes.json();
            const trendsData = await trendsRes.json();
            const briefingData = await briefingRes.json();

            setItems(itemsData.items || []);
            setTrends(trendsData.trends || []);
            setBriefing(briefingData.status === 'no_briefing' ? null : briefingData);
        } catch (error) {
            console.error('Failed to fetch intel data:', error);
        } finally {
            setLoading(false);
        }
    };

    const getRelevanceLevel = (score) => {
        if (score >= 80) return 'high';
        if (score >= 50) return 'medium';
        return 'low';
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-foreground mb-2">Market Intelligence</h1>
                <p className="text-muted-foreground">
                    Real-time news synthesis, regulatory tracking, and emerging trend analysis.
                </p>
            </div>

            {/* Weekly Briefing */}
            {briefing && (
                <Card className="border-primary/30 bg-gradient-to-br from-primary/5 to-transparent">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <FileText className="h-5 w-5 text-primary" />
                            Weekly Synthesis
                        </CardTitle>
                        <CardDescription>Week of {new Date(briefing.week_starting).toLocaleDateString()}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div>
                            <h3 className="font-semibold text-sm mb-2">Executive Summary</h3>
                            <p className="text-sm text-muted-foreground">{briefing.summary}</p>
                        </div>
                        {briefing.emerging_trends && briefing.emerging_trends.length > 0 && (
                            <div>
                                <h3 className="font-semibold text-sm mb-2">Emerging Trends</h3>
                                <div className="flex flex-wrap gap-2">
                                    {briefing.emerging_trends.map((trend, idx) => (
                                        <span key={idx} className="text-xs px-2 py-1 bg-primary/10 text-primary rounded">
                                            {trend}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                        {briefing.action_items && briefing.action_items.length > 0 && (
                            <div>
                                <h3 className="font-semibold text-sm mb-2">Action Items</h3>
                                <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
                                    {briefing.action_items.map((item, idx) => (
                                        <li key={idx}>{item}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Intelligence Feed */}
                <div className="lg:col-span-2">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Newspaper className="h-5 w-5 text-blue-400" />
                                Intelligence Feed
                            </CardTitle>
                            <CardDescription>Latest market signals and regulatory updates</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {items.length === 0 ? (
                                <p className="text-center text-muted-foreground py-8">
                                    No intelligence items available. Run an intel scan to populate the feed.
                                </p>
                            ) : (
                                <div className="space-y-4">
                                    {items.map((item) => (
                                        <div
                                            key={item.id}
                                            className="p-4 rounded-lg border border-border/50 bg-background/50 hover:bg-surface-hover transition-colors"
                                        >
                                            <div className="flex items-start justify-between gap-3 mb-2">
                                                <h3 className="font-semibold text-foreground">{item.title}</h3>
                                                <div className="flex items-center gap-2 flex-shrink-0">
                                                    <span className={`text-xs font-medium ${RELEVANCE_COLORS[getRelevanceLevel(item.relevance_score)]}`}>
                                                        {item.relevance_score}%
                                                    </span>
                                                </div>
                                            </div>
                                            <p className="text-sm text-muted-foreground mb-3">{item.summary}</p>
                                            <div className="flex items-center justify-between">
                                                <span className={`text-xs px-2 py-1 rounded ${CATEGORY_COLORS[item.category] || 'bg-muted text-muted-foreground'}`}>
                                                    {item.category}
                                                </span>
                                                <span className="text-xs text-muted-foreground">
                                                    {new Date(item.published_date).toLocaleDateString()}
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Market Trends */}
                <div>
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <TrendingUp className="h-5 w-5 text-emerald-400" />
                                Market Trends
                            </CardTitle>
                            <CardDescription>Emerging patterns and signals</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {trends.length === 0 ? (
                                <p className="text-center text-muted-foreground py-8 text-sm">
                                    No trends detected yet.
                                </p>
                            ) : (
                                <div className="space-y-4">
                                    {trends.map((trend) => (
                                        <div key={trend.id} className="p-3 rounded-lg border border-border/50 bg-background/30">
                                            <h3 className="font-semibold text-sm mb-1">{trend.name}</h3>
                                            <div className="flex items-center gap-2 mb-2">
                                                <span className="text-xs px-2 py-0.5 bg-muted rounded">{trend.sector}</span>
                                                <span className={`text-xs px-2 py-0.5 rounded ${trend.strength === 'accelerating' ? 'bg-emerald-500/20 text-emerald-300' :
                                                        trend.strength === 'emerging' ? 'bg-blue-500/20 text-blue-300' :
                                                            'bg-slate-500/20 text-slate-300'
                                                    }`}>
                                                    {trend.strength}
                                                </span>
                                            </div>
                                            {trend.implications && (
                                                <p className="text-xs text-muted-foreground mt-2">{trend.implications}</p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
