import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/Tooltip';
import { Download, Search, Filter, HelpCircle, Loader2, X, Info, CheckCircle2, AlertCircle, BarChart3 as ChartIcon, MapPin } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    PieChart, Pie, Cell,
    BarChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip as RechartsTooltip, Legend, ResponsiveContainer
} from 'recharts';
import Methodology from './Methodology';

export default function UniverseTable() {
    const [companies, setCompanies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [scanStatus, setScanStatus] = useState(null);
    const [showFilters, setShowFilters] = useState(false);
    const [showAnalytics, setShowAnalytics] = useState(false);
    const [filters, setFilters] = useState({
        tier: '',
        sector: '',
        country: '',
        minMoat: '',
        isEnriched: '',
        isScored: ''
    });
    const [stats, setStats] = useState(null);

    // Poll for scan status
    useEffect(() => {
        const pollStatus = async () => {
            try {
                const status = await api.getUniverseStatus();
                setScanStatus(status);

                // Fetch stats if scan is running
                if (status.status === 'running') {
                    const statsData = await api.getUniverseStats();
                    setStats(statsData);
                }
            } catch (e) {
                console.error("Status Poll Error", e);
            }
        };

        pollStatus(); // Initial call
        const interval = setInterval(pollStatus, 5000);
        return () => clearInterval(interval);
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [companiesResponse, statsResponse] = await Promise.all([
                api.getCompanies({
                    limit: 100,
                    search: searchTerm || undefined,
                    tier: filters.tier || undefined,
                    sector: filters.sector || undefined,
                    country: filters.country || undefined,
                    min_moat: filters.minMoat ? parseInt(filters.minMoat) : undefined,
                    is_enriched: filters.isEnriched === 'true' ? true : filters.isEnriched === 'false' ? false : undefined,
                    is_scored: filters.isScored === 'true' ? true : filters.isScored === 'false' ? false : undefined
                }),
                api.getUniverseStats()
            ]);
            setCompanies(companiesResponse.data || companiesResponse);
            setStats(statsResponse);
        } catch (error) {
            console.error("Failed to fetch data", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const handler = setTimeout(() => {
            fetchData();
        }, 300);
        return () => clearTimeout(handler);
    }, [searchTerm, filters]);

    const handleFilterChange = (key, value) => {
        setFilters(prev => ({ ...prev, [key]: value }));
    };

    const clearFilters = () => {
        setFilters({
            tier: '',
            sector: '',
            country: '',
            minMoat: '',
            isEnriched: '',
            isScored: ''
        });
        setSearchTerm('');
    };

    const handleExport = () => {
        window.open(api.getUniverseExportUrl(), '_blank');
    };

    const getPillarScore = (analysis, key) => {
        if (!analysis) return { score: 0, justification: 'No analysis available.' };
        const data = typeof analysis === 'string' ? JSON.parse(analysis) : analysis;
        return data[key] || { score: 0, justification: 'N/A' };
    };

    const PillarCell = ({ analysis, type }) => {
        const { score, justification } = getPillarScore(analysis, type);

        let colorClass = "text-muted-foreground";
        if (score >= 80) colorClass = "text-emerald-400 font-bold";
        else if (score >= 60) colorClass = "text-green-300";
        else if (score >= 40) colorClass = "text-yellow-300";
        else if (score > 0) colorClass = "text-orange-300";

        return (
            <div className="relative group/cell flex justify-center">
                <span className={`cursor-help ${colorClass}`}>{score > 0 ? score : '-'}</span>

                {score > 0 && (
                    <div className="absolute z-50 w-64 p-3 mt-6 bg-slate-900 border border-border rounded-lg shadow-xl hidden group-hover/cell:block left-1/2 -translate-x-1/2 pointer-events-none">
                        <div className="text-xs font-semibold text-white mb-1 uppercase tracking-wider">{type}</div>
                        <p className="text-xs text-slate-300 leading-snug">{justification}</p>
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="space-y-6">
            <Methodology />

            <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                    <div>
                        <div className="flex items-center gap-3">
                            <CardTitle className="text-xl">Target Universe</CardTitle>
                            {scanStatus?.status === 'running' && (
                                <Badge className="bg-primary/20 text-primary border-primary/30 animate-pulse">
                                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                    Scanning Active: {scanStatus.current_action}
                                </Badge>
                            )}
                        </div>
                        <CardDescription>
                            Comprehensive database of potential investment targets.
                            {scanStatus?.stats?.total_found > 0 && (
                                <span className="ml-2 text-primary">
                                    ({scanStatus.stats.total_found} found in current session)
                                </span>
                            )}
                        </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="relative">
                            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                            <input
                                type="search"
                                placeholder="Search companies..."
                                className="h-10 w-[250px] rounded-lg border border-input bg-background pl-9 pr-4 text-sm outline-none focus:ring-1 focus:ring-ring"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </div>
                        <Button variant="outline" size="icon" onClick={fetchData} title="Refresh Data">
                            <Loader2 className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                        </Button>
                        <Button
                            variant={showAnalytics ? "default" : "outline"}
                            size="icon"
                            onClick={() => setShowAnalytics(!showAnalytics)}
                            className={showAnalytics ? "bg-accent-main" : ""}
                            title="Toggle Advanced Analytics"
                        >
                            <ChartIcon className="h-4 w-4" />
                        </Button>
                        <Button
                            variant={showFilters ? "default" : "outline"}
                            size="icon"
                            onClick={() => setShowFilters(!showFilters)}
                            className={showFilters ? "bg-accent-main" : ""}
                            title="Toggle Filters"
                        >
                            <Filter className="h-4 w-4" />
                        </Button>
                        <Button onClick={handleExport} className="gap-2 bg-accent-main hover:bg-accent-main/90 text-text-pri">
                            <Download className="h-4 w-4" />
                            Export CSV
                        </Button>
                    </div>
                </CardHeader>

                <AnimatePresence>
                    {showAnalytics && stats && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="bg-muted/10 border-b border-border/30 overflow-hidden"
                        >
                            <AdvancedAnalytics stats={stats} />
                        </motion.div>
                    )}
                </AnimatePresence>

                <AnimatePresence>
                    {stats && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="bg-muted/30 border-y border-border/30 overflow-hidden"
                        >
                            <FunnelOverview stats={stats} />
                        </motion.div>
                    )}
                </AnimatePresence>

                <AnimatePresence>
                    {showFilters && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="px-6 pb-4 overflow-hidden"
                        >
                            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 p-4 rounded-lg bg-background/40 border border-border/30">
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold uppercase text-muted-foreground">Tier</label>
                                    <Select
                                        value={filters.tier}
                                        onChange={(e) => handleFilterChange('tier', e.target.value)}
                                    >
                                        <option value="">All Tiers</option>
                                        <option value="1A">Tier 1A (£15M+, High Moat)</option>
                                        <option value="1B">Tier 1B (£15M+, Mod Moat)</option>
                                        <option value="2">Tier 2 (Watch)</option>
                                        <option value="waitlist">Waitlist</option>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold uppercase text-muted-foreground">Sector</label>
                                    <Input
                                        placeholder="Filter by sector..."
                                        value={filters.sector}
                                        onChange={(e) => handleFilterChange('sector', e.target.value)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold uppercase text-muted-foreground">Country</label>
                                    <Input
                                        placeholder="e.g. GB, FR, DE"
                                        value={filters.country}
                                        onChange={(e) => handleFilterChange('country', e.target.value)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold uppercase text-muted-foreground">Min Moat</label>
                                    <Input
                                        type="number"
                                        min="0"
                                        max="100"
                                        placeholder="0-100"
                                        value={filters.minMoat}
                                        onChange={(e) => handleFilterChange('minMoat', e.target.value)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold uppercase text-muted-foreground">Enrichment</label>
                                    <Select
                                        value={filters.isEnriched}
                                        onChange={(e) => handleFilterChange('isEnriched', e.target.value)}
                                    >
                                        <option value="">All</option>
                                        <option value="true">Enriched Only</option>
                                        <option value="false">Not Enriched</option>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold uppercase text-muted-foreground">Scoring</label>
                                    <Select
                                        value={filters.isScored}
                                        onChange={(e) => handleFilterChange('isScored', e.target.value)}
                                    >
                                        <option value="">All</option>
                                        <option value="true">Scored Only</option>
                                        <option value="false">Not Scored</option>
                                    </Select>
                                </div>
                                <div className="md:col-span-3 lg:col-span-6 flex justify-end items-end">
                                    <Button variant="ghost" size="sm" onClick={clearFilters} className="text-xs gap-1 h-8">
                                        <X className="h-3 w-3" />
                                        Clear All
                                    </Button>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
                <CardContent>
                    <div className="rounded-md border border-border/50 bg-background/50 overflow-visible">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead className="w-[200px]">Company</TableHead>
                                    <TableHead>Revenue</TableHead>
                                    <TableHead>Enrichment</TableHead>
                                    <TableHead className="text-center w-16" title="Regulatory">Reg</TableHead>
                                    <TableHead className="text-center w-16" title="Network Effects">Net</TableHead>
                                    <TableHead className="text-center w-16" title="Intellectual Property">IP</TableHead>
                                    <TableHead className="text-center w-16" title="Brand">Brand</TableHead>
                                    <TableHead className="text-center w-16" title="Cost Advantage">Cost</TableHead>
                                    <TableHead className="text-center w-16 font-bold">Total</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading && companies.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={8} className="text-center h-24 text-muted-foreground">
                                            Loading universe data...
                                        </TableCell>
                                    </TableRow>
                                ) : companies.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={8} className="text-center h-24 text-muted-foreground">
                                            No companies found matching criteria.
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    companies.map((cls, idx) => (
                                        <TableRow
                                            key={cls.id || idx}
                                            className="group cursor-pointer hover:bg-indigo-950/20"
                                        >
                                            <TableCell>
                                                <div className="font-medium text-indigo-200">{cls.name}</div>
                                                <div className="text-xs text-muted-foreground">
                                                    {cls.sector}
                                                    {cls.sub_sector && <span className="text-indigo-300"> • {cls.sub_sector}</span>}
                                                </div>
                                                {(cls.hq_city || cls.hq_country) && (
                                                    <div className="text-[10px] text-muted-foreground/70 flex items-center gap-1 mt-0.5">
                                                        <MapPin className="h-3 w-3" />
                                                        {[cls.hq_city, cls.hq_country === 'GB' ? 'UK' : cls.hq_country].filter(Boolean).join(', ')}
                                                    </div>
                                                )}
                                                {cls.description && (
                                                    <TooltipProvider>
                                                        <Tooltip>
                                                            <TooltipTrigger asChild>
                                                                <div className="text-[10px] text-muted-foreground/50 truncate max-w-[200px] mt-1 cursor-help italic">
                                                                    {cls.description}
                                                                </div>
                                                            </TooltipTrigger>
                                                            <TooltipContent side="right" className="max-w-sm bg-slate-900 border-slate-800 text-slate-300">
                                                                {cls.description}
                                                            </TooltipContent>
                                                        </Tooltip>
                                                    </TooltipProvider>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                {cls.revenue_gbp
                                                    ? `£${(cls.revenue_gbp / 1000000).toFixed(1)}M`
                                                    : '-'}
                                            </TableCell>
                                            <TableCell>
                                                <EnrichmentStatus company={cls} />
                                            </TableCell>
                                            <TableCell><PillarCell analysis={cls.moat_analysis} type="regulatory" /></TableCell>
                                            <TableCell><PillarCell analysis={cls.moat_analysis} type="network" /></TableCell>
                                            <TableCell><PillarCell analysis={cls.moat_analysis} type="ip" /></TableCell>
                                            <TableCell><PillarCell analysis={cls.moat_analysis} type="liability" /></TableCell>
                                            <TableCell><PillarCell analysis={cls.moat_analysis} type="physical" /></TableCell>
                                            <TableCell className="text-center font-bold text-white">
                                                {cls.moat_score > 0 ? cls.moat_score : '-'}
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

function AdvancedAnalytics({ stats }) {
    const COLORS = ['#a855f7', '#6366f1', '#64748b', '#f59e0b', '#ef4444'];

    // Enrichment Data
    const enrichmentData = Object.entries(stats.enrichmentStatus).map(([name, value]) => ({ name, value }));

    // Exclusion Data
    const exclusionData = Object.entries(stats.exclusionBreakdown)
        .map(([name, value]) => ({ name: name.split('>')[0].trim(), value }))
        .sort((a, b) => b.value - a.value);

    // Moat Data
    const moatData = Object.entries(stats.moatRangeBreakdown).map(([name, value]) => ({ name, value }));

    return (
        <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Enrichment Split */}
            <div className="space-y-4">
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-indigo-500" />
                    Enrichment Funnel Split
                </h4>
                <div className="h-[200px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={enrichmentData}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                paddingAngle={5}
                                dataKey="value"
                            >
                                {enrichmentData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Pie>
                            <RechartsTooltip
                                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                                itemStyle={{ color: '#f8fafc' }}
                            />
                            <Legend />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Exclusion Reasons */}
            <div className="space-y-4">
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-warning" />
                    Exclusion Breakdown
                </h4>
                <div className="h-[200px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={exclusionData} layout="vertical">
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                            <XAxis type="number" hide />
                            <YAxis
                                dataKey="name"
                                type="category"
                                width={100}
                                tick={{ fontSize: 10, fill: '#94a3b8' }}
                            />
                            <RechartsTooltip
                                cursor={{ fill: 'transparent' }}
                                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                                itemStyle={{ color: '#f8fafc' }}
                            />
                            <Bar dataKey="value" fill="#f59e0b" radius={[0, 4, 4, 0]} barSize={20} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Moat Distribution */}
            <div className="space-y-4">
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-emerald-500" />
                    Moat Score Distribution
                </h4>
                <div className="h-[200px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={moatData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                            <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#94a3b8' }} />
                            <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} />
                            <RechartsTooltip
                                cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                                itemStyle={{ color: '#f8fafc' }}
                            />
                            <Bar dataKey="value" fill="#10b981" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
}

function FunnelOverview({ stats }) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-0 divide-x divide-border/30 bg-background/20">
            <div className="p-4 flex flex-col gap-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Discovery Pipeline</span>
                <span className="text-2xl font-bold text-white">{stats.totalDiscovery}</span>
                <div className="h-1 w-full bg-muted/50 rounded-full mt-2 overflow-hidden">
                    <div className="h-full bg-primary" style={{ width: '100%' }} />
                </div>
            </div>
            <div className="p-4 flex flex-col gap-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Enriched (Zone 2)</span>
                <span className="text-2xl font-bold text-indigo-300">{stats.enriched}</span>
                <div className="h-1 w-full bg-muted/50 rounded-full mt-2 overflow-hidden">
                    <div
                        className="h-full bg-indigo-400"
                        style={{ width: `${(stats.enriched / stats.totalDiscovery * 100) || 0}%` }}
                    />
                </div>
            </div>
            <div className="p-4 flex flex-col gap-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Scored (Zone 3)</span>
                <span className="text-2xl font-bold text-emerald-400">{stats.scored}</span>
                <div className="h-1 w-full bg-muted/50 rounded-full mt-2 overflow-hidden">
                    <div
                        className="h-full bg-emerald-500"
                        style={{ width: `${(stats.scored / stats.totalDiscovery * 100) || 0}%` }}
                    />
                </div>
            </div>
            <div className="p-4 flex flex-col gap-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Exclusions</span>
                <span className="text-2xl font-bold text-warning">{stats.excluded}</span>
                <div className="h-1 w-full bg-muted/50 rounded-full mt-2 overflow-hidden">
                    <div
                        className="h-full bg-warning"
                        style={{ width: `${(stats.excluded / stats.totalDiscovery * 100) || 0}%` }}
                    />
                </div>
                {stats.exclusionBreakdown && Object.keys(stats.exclusionBreakdown).length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                        {Object.entries(stats.exclusionBreakdown).slice(0, 2).map(([reason, count]) => (
                            <Badge key={reason} variant="outline" className="text-[9px] h-4 bg-warning/5 text-warning/80 border-warning/10">
                                {reason}: {count}
                            </Badge>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

function EnrichmentStatus({ company }) {
    if (company.moat_score > 0) {
        return (
            <Badge variant="outline" className="bg-success/10 text-success border-success/20 gap-1">
                <CheckCircle2 className="h-3 w-3" />
                Scored
            </Badge>
        );
    }

    if (company.description) {
        return (
            <Badge variant="outline" className="bg-accent-main/10 text-accent-main border-accent-main/20 gap-1">
                <CheckCircle2 className="h-3 w-3" />
                Enriched
            </Badge>
        );
    }

    if (company.exclusion_reason) {
        return (
            <TooltipProvider>
                <Tooltip>
                    <TooltipTrigger asChild>
                        <Badge variant="secondary" className="bg-warning/10 text-warning border-warning/20 gap-1 cursor-help">
                            <AlertCircle className="h-3 w-3" />
                            Excluded
                        </Badge>
                    </TooltipTrigger>
                    <TooltipContent>
                        <p className="max-w-xs">{company.exclusion_reason}</p>
                    </TooltipContent>
                </Tooltip>
            </TooltipProvider>
        );
    }

    return (
        <Badge variant="outline" className="bg-muted/10 text-muted-foreground border-muted-foreground/20 gap-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            Pending
        </Badge>
    );
}
