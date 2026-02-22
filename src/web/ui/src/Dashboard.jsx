import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import { motion } from 'framer-motion';
import { useCurrency } from '@/context/CurrencyContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { KPICard } from '@/components/ui/KPICard';
import { MoatBreakdown } from '@/components/ui/MoatBreakdown';
import {
    Building2,
    Target,
    Bell,
    TrendingUp,
    ArrowRight,
    Radio,
    Coins,
    Clock,
    ChevronRight,
    Flame,
    Sparkles,
    RefreshCw
} from 'lucide-react';

export default function Dashboard() {
    const navigate = useNavigate();
    const { convert, currency } = useCurrency();

    // Helper to format large numbers with currency conversion
    const formatMoney = (amount) => {
        if (!amount) return '—';
        const converted = convert(amount); // Default from GBP
        const symbol = currency === 'USD' ? '$' : currency === 'EUR' ? '€' : '£';
        return `${symbol}${(converted / 1000000).toFixed(1)}M`;
    };

    const [stats, setStats] = useState({
        totalCompanies: 0,
        trackedCompanies: 0,
        activeAlerts: 0,
        recentDeals: 0,
        loading: true
    });
    const [recentStats, setRecentStats] = useState(null);
    const [activity, setActivity] = useState([]);
    const [alerts, setAlerts] = useState([]);
    const [tier1ACompanies, setTier1ACompanies] = useState([]);
    const [hotSectors, setHotSectors] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchDashboardData = async () => {
            try {
                // Fetch all data in parallel
                // api.get returns the data object directly (or null if caught)
                const [statsData, alertsData, activityData, tier1A, sectors, recentStatsData] = await Promise.all([
                    api.getDashboardStats().catch(() => null),
                    api.getAlerts({ unread_only: true, limit: 5 }).catch(() => null),
                    api.getDashboardActivity({ limit: 10 }).catch(() => null),
                    api.getCompanies({ tier: 'TIER_1A', limit: 5 }).catch(() => null),
                    api.getHotSectors().catch(() => null),
                    api.getUniverseRecentStats().catch(() => null)
                ]);

                // 1. Stats
                if (statsData) {
                    setStats({
                        totalCompanies: statsData.total_companies || 0,
                        trackedCompanies: statsData.tracked_companies || 0,
                        activeAlerts: statsData.active_alerts || 0,
                        recentDeals: statsData.recent_deals || 0,
                        loading: false
                    });
                } else {
                    // Fallback to zeros if stats fail
                    setStats(prev => ({ ...prev, loading: false, totalCompanies: 0, trackedCompanies: 0, activeAlerts: 0, recentDeals: 0 }));
                }

                // 2. Alerts
                if (alertsData) {
                    setAlerts(alertsData);
                }

                // 3. Activity
                if (activityData) {
                    setActivity(activityData);
                }

                // 4. Tier 1A Companies
                if (tier1A) {
                    // Sort by moat score just in case API didn't
                    tier1A.sort((a, b) => (b.moat_score || 0) - (a.moat_score || 0));
                    setTier1ACompanies(tier1A);
                }

                // 5. Hot Sectors
                if (sectors) {
                    setHotSectors(sectors.slice(0, 3));
                }

                if (recentStatsData) {
                    setRecentStats(recentStatsData);
                }

            } catch (error) {
                console.error('Failed to fetch dashboard data:', error);
                setStats(prev => ({ ...prev, loading: false }));
            } finally {
                setLoading(false);
            }
        };

        fetchDashboardData();
    }, []);

    const formatTimeAgo = (timestamp) => {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000 / 60);
        if (diff < 60) return `${diff}m ago`;
        if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
        return `${Math.floor(diff / 1440)}d ago`;
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <header>
                <h1 className="text-2xl font-bold text-text-pri">Dashboard</h1>
                <p className="text-text-sec text-sm mt-1">Real-time intelligence and market tracking overview.</p>
            </header>

            {/* Recent Discovery Stats */}
            {recentStats && (
                <Card className="border-border-subtle bg-surface">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-base flex items-center gap-2">
                            <Sparkles className="h-4 w-4 text-primary" />
                            Recently Added
                        </CardTitle>
                        <p className="text-xs text-text-sec">
                            Companies discovered or enriched in the last 24h, 5 days, 30 days.
                        </p>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
                            <div className="flex items-center gap-2 p-2 rounded-lg bg-surface-alt">
                                <span className="text-xs text-text-ter">Discovered 24h</span>
                                <span className="font-semibold text-text-pri">{recentStats.discovered_24h ?? 0}</span>
                            </div>
                            <div className="flex items-center gap-2 p-2 rounded-lg bg-surface-alt">
                                <span className="text-xs text-text-ter">5d</span>
                                <span className="font-semibold text-text-pri">{recentStats.discovered_5d ?? 0}</span>
                            </div>
                            <div className="flex items-center gap-2 p-2 rounded-lg bg-surface-alt">
                                <span className="text-xs text-text-ter">30d</span>
                                <span className="font-semibold text-text-pri">{recentStats.discovered_30d ?? 0}</span>
                            </div>
                            <div className="flex items-center gap-2 p-2 rounded-lg bg-surface-alt">
                                <RefreshCw className="h-3 w-3 text-text-ter" />
                                <span className="text-xs text-text-ter">Enriched 24h</span>
                                <span className="font-semibold text-text-pri">{recentStats.enriched_24h ?? 0}</span>
                            </div>
                            <div className="flex items-center gap-2 p-2 rounded-lg bg-surface-alt">
                                <span className="text-xs text-text-ter">5d</span>
                                <span className="font-semibold text-text-pri">{recentStats.enriched_5d ?? 0}</span>
                            </div>
                            <div className="flex items-center gap-2 p-2 rounded-lg bg-surface-alt">
                                <span className="text-xs text-text-ter">30d</span>
                                <span className="font-semibold text-text-pri">{recentStats.enriched_30d ?? 0}</span>
                            </div>
                        </div>
                        <button
                            onClick={() => navigate('/universe')}
                            className="mt-3 text-xs text-primary hover:text-primary-light flex items-center gap-1"
                        >
                            View & filter by recency <ChevronRight className="h-3 w-3" />
                        </button>
                    </CardContent>
                </Card>
            )}

            {/* KPI Cards Row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <KPICard
                    title="Total Companies"
                    value={stats.loading ? '—' : stats.totalCompanies.toLocaleString()}
                    icon={Building2}
                    loading={stats.loading}
                />
                <KPICard
                    title="Companies Tracked"
                    value={stats.loading ? '—' : stats.trackedCompanies.toLocaleString()}
                    icon={Target}
                    change="+12 this week"
                    changeType="positive"
                    loading={stats.loading}
                />
                <KPICard
                    title="Active Alerts"
                    value={stats.loading ? '—' : stats.activeAlerts}
                    icon={Bell}
                    change="3 unread"
                    changeType="neutral"
                    loading={stats.loading}
                />
                <KPICard
                    title="Recent Deals"
                    value={stats.loading ? '—' : stats.recentDeals}
                    icon={TrendingUp}
                    change="+5 this month"
                    changeType="positive"
                    loading={stats.loading}
                />
            </div>

            {/* Two Column Row */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                {/* Recent Activity Feed - 60% */}
                <Card className="lg:col-span-3 border-border-subtle bg-surface">
                    <CardHeader className="flex flex-row items-center justify-between pb-4">
                        <div className="flex items-center gap-2">
                            <Clock className="h-5 w-5 text-primary" />
                            <CardTitle className="text-lg">Recent Activity</CardTitle>
                        </div>
                        <button
                            onClick={() => navigate('/competitive')}
                            className="text-xs text-primary hover:text-primary-light flex items-center gap-1"
                        >
                            View All <ChevronRight className="h-3 w-3" />
                        </button>
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <div className="space-y-3">
                                {[1, 2, 3].map(i => (
                                    <div key={i} className="animate-pulse flex gap-3">
                                        <div className="h-8 w-8 bg-surface-alt rounded-lg" />
                                        <div className="flex-1">
                                            <div className="h-4 w-3/4 bg-surface-alt rounded mb-2" />
                                            <div className="h-3 w-1/2 bg-surface-alt rounded" />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : activity.length === 0 ? (
                            <p className="text-text-sec text-sm text-center py-8">No recent activity</p>
                        ) : (
                            <div className="space-y-3">
                                {activity.map((item) => {
                                    const Icon = item.icon || TrendingUp;
                                    return (
                                        <motion.div
                                            key={item.id}
                                            initial={{ opacity: 0, x: -10 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            className="flex items-start gap-3 p-3 rounded-lg hover:bg-surface-hover transition-colors cursor-pointer"
                                        >
                                            <div className={`p-2 rounded-lg bg-surface-alt`}>
                                                <Icon className={`h-4 w-4 ${item.color || 'text-primary'}`} />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium text-text-pri truncate">{item.title}</p>
                                                <p className="text-xs text-text-sec truncate">{item.description}</p>
                                            </div>
                                            <span className="text-xs text-text-ter whitespace-nowrap">
                                                {formatTimeAgo(item.timestamp)}
                                            </span>
                                        </motion.div>
                                    );
                                })}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Right Side - 40% */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Unread Alerts */}
                    <Card className="border-border-subtle bg-surface">
                        <CardHeader className="pb-3">
                            <div className="flex items-center gap-2">
                                <Bell className="h-5 w-5 text-warning" />
                                <CardTitle className="text-lg">Unread Alerts</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-2">
                                {loading ? (
                                    <p className="text-xs text-text-sec text-center py-4">Loading alerts...</p>
                                ) : alerts.length === 0 ? (
                                    <p className="text-xs text-text-sec text-center py-4">No unread alerts</p>
                                ) : (
                                    alerts.map((alert) => (
                                        <div
                                            key={alert.id}
                                            className="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-hover transition-colors cursor-pointer"
                                        >
                                            <span className={`h-2 w-2 rounded-full ${alert.priority === 'high' ? 'bg-danger' :
                                                alert.priority === 'medium' ? 'bg-warning' : 'bg-primary'
                                                }`} />
                                            <div className="flex-1 min-w-0">
                                                <span className="text-sm text-text-pri block truncate">{alert.message}</span>
                                                <span className="text-xs text-text-ter">{formatTimeAgo(alert.created_at)}</span>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                            <button
                                onClick={() => navigate('/tracker')}
                                className="w-full mt-3 text-xs text-primary hover:text-primary-light flex items-center justify-center gap-1"
                            >
                                View All Alerts <ChevronRight className="h-3 w-3" />
                            </button>
                        </CardContent>
                    </Card>

                    {/* Hot Sectors */}
                    <Card className="border-border-subtle bg-surface">
                        <CardHeader className="pb-3">
                            <div className="flex items-center gap-2">
                                <Flame className="h-5 w-5 text-orange-400" />
                                <CardTitle className="text-lg">Hot Sectors</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-3">
                                {hotSectors.length > 0 ? (
                                    hotSectors.map((item, idx) => (
                                        <div key={idx} className="flex items-center justify-between">
                                            <div>
                                                <p className="text-sm font-medium text-text-pri">{item.sector}</p>
                                                <p className="text-xs text-text-sec">{item.deal_count} deals</p>
                                            </div>
                                            <Badge className="bg-success/10 text-success border-0">
                                                +{item.deal_growth_pct || 0}%
                                            </Badge>
                                        </div>
                                    ))
                                ) : (
                                    <p className="text-xs text-text-sec text-center py-4">Scanning market for trends...</p>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>

            {/* Top Tier 1A Targets - Full Width */}
            <Card className="border-border-subtle bg-surface">
                <CardHeader className="flex flex-row items-center justify-between pb-4">
                    <div className="flex items-center gap-2">
                        <Target className="h-5 w-5 text-primary" />
                        <CardTitle className="text-lg">Top Tier 1A Targets</CardTitle>
                    </div>
                    <button
                        onClick={() => navigate('/universe?tier=1A')}
                        className="text-xs text-primary hover:text-primary-light flex items-center gap-1"
                    >
                        View All <ChevronRight className="h-3 w-3" />
                    </button>
                </CardHeader>
                <CardContent>
                    <div className="rounded-lg border border-border-subtle overflow-hidden">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-surface-alt hover:bg-surface-alt">
                                    <TableHead className="text-text-ter">Company</TableHead>
                                    <TableHead className="text-text-ter text-center">Moat Score</TableHead>
                                    <TableHead className="text-text-ter text-right">Revenue</TableHead>
                                    <TableHead className="text-text-ter">Sector</TableHead>
                                    <TableHead className="text-text-ter w-8"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    <TableRow>
                                        <TableCell colSpan={5} className="text-center py-8 text-text-sec">
                                            Loading top targets...
                                        </TableCell>
                                    </TableRow>
                                ) : tier1ACompanies.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={5} className="text-center py-8 text-text-sec">
                                            No Tier 1A companies found. Run the Universe Scanner to populate data.
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    tier1ACompanies.map((company) => (
                                        <TableRow
                                            key={company.id}
                                            onClick={() => navigate(`/tracker?company=${company.id}`)}
                                            className="cursor-pointer hover:bg-surface-hover transition-colors"
                                        >
                                            <TableCell>
                                                <div>
                                                    <p className="font-medium text-text-pri">{company.name}</p>
                                                    <div className="flex items-center gap-2 mt-1">
                                                        <p className="text-xs text-text-sec">{company.hq_country || 'UK'}</p>
                                                        <MoatBreakdown attributes={company.moat_attributes} />
                                                    </div>
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-center">
                                                <span className={`font-bold text-lg ${(company.moat_score || 0) >= 80 ? 'text-success' :
                                                    (company.moat_score || 0) >= 60 ? 'text-warning' : 'text-text-sec'
                                                    }`}>
                                                    {company.moat_score || '—'}
                                                </span>
                                            </TableCell>
                                            <TableCell className="text-right font-mono">
                                                {formatMoney(company.revenue_gbp)}
                                            </TableCell>
                                            <TableCell>
                                                <Badge variant="outline" className="text-text-sec border-border-subtle">
                                                    {company.sector || 'Unknown'}
                                                </Badge>
                                            </TableCell>
                                            <TableCell>
                                                <ArrowRight className="h-4 w-4 text-text-ter" />
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
