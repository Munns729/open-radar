import React, { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent } from "@/components/ui/Card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Download, FileText, Loader2 } from "lucide-react";

export default function Reports() {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [stats, setStats] = useState({ count: 0 });

    // Filters
    const [filters, setFilters] = useState({
        tier: 'all',
        sector: '',
        min_moat: 0,
        max_moat: 100,
        hot_only: false
    });

    const [exporting, setExporting] = useState(false);

    useEffect(() => {
        const fetchPreview = async () => {
            setLoading(true);
            try {
                const params = {
                    tier: filters.tier !== 'all' ? filters.tier : undefined,
                    sector: filters.sector || undefined,
                    hot_only: filters.hot_only ? 'true' : undefined,
                    min_moat: filters.min_moat,
                    max_moat: filters.max_moat
                };

                const data = await api.previewReport(params);
                // api.get (via previewReport) returns data directly
                setData(data || []);
                setStats({ count: (data || []).length });
            } catch (err) {
                console.error("Preview fetch error:", err);
            } finally {
                setLoading(false);
            }
        };

        const debounce = setTimeout(fetchPreview, 400);
        return () => clearTimeout(debounce);
    }, [filters]);

    const handleExport = async (format) => {
        setExporting(true);
        try {
            const params = {
                format,
                tier: filters.tier !== 'all' ? filters.tier : undefined,
                sector: filters.sector || undefined,
                hot_only: filters.hot_only ? 'true' : undefined,
                min_moat: filters.min_moat,
                max_moat: filters.max_moat
            };

            const data = await api.generateReport(params);
            if (data && data.filename) {
                window.open(api.getReportDownloadUrl(data.filename), '_blank');
            }
        } catch (err) {
            console.error("Export error:", err);
        } finally {
            setExporting(false);
        }
    };

    const getScoreColor = (score) => {
        if (score >= 85) return "text-priority-hot-text font-semibold";
        if (score >= 75) return "text-priority-high-text font-semibold";
        if (score >= 65) return "text-priority-med-text font-semibold";
        return "text-priority-low-text font-semibold";
    };

    return (
        <div className="space-y-6 font-sans text-text-pri">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-[20px] font-semibold tracking-[0.12em] text-text-pri uppercase">Live Reporting</h1>
                    <p className="text-text-sec mt-2 text-sm">Real-time filter and export of target universe.</p>
                </div>
                <div className="flex gap-2">
                    <Button
                        variant="outline"
                        onClick={() => handleExport('html')}
                        disabled={exporting}
                        className="border-border-main bg-surface hover:bg-surface-hover text-text-pri"
                    >
                        {exporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                        Export HTML
                    </Button>
                    <Button
                        className="bg-priority-low-bg hover:bg-surface-hover text-text-pri border border-border-main"
                        onClick={() => handleExport('excel')}
                        disabled={exporting}
                    >
                        {exporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileText className="mr-2 h-4 w-4" />}
                        Export Excel
                    </Button>
                </div>
            </div>

            {/* Filters Bar */}
            <Card className="border-border-main bg-surface shadow-none rounded-lg">
                <CardContent className="p-4 flex flex-wrap gap-4 items-end">

                    <div className="space-y-2">
                        <label className="text-[11px] font-semibold text-text-ter uppercase tracking-[0.1em] px-1">Tier</label>
                        <div className="flex bg-surface-alt p-1 rounded-lg border border-border-subtle">
                            {['all', '1A', '1B', 'both'].map(t => (
                                <button
                                    key={t}
                                    onClick={() => setFilters({ ...filters, tier: t })}
                                    className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${filters.tier === t
                                        ? 'bg-surface hover:bg-surface-hover text-text-pri border border-border-main shadow-none'
                                        : 'text-text-sec hover:text-text-pri hover:bg-surface-hover'
                                        }`}
                                >
                                    {t.toUpperCase()}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="space-y-2 min-w-[250px]">
                        <label className="text-[11px] font-semibold text-text-ter uppercase tracking-[0.1em] px-1">Sector Search</label>
                        <div className="relative group">
                            <input
                                type="text"
                                placeholder="E.g. Defence"
                                value={filters.sector}
                                onChange={(e) => setFilters({ ...filters, sector: e.target.value })}
                                className="w-full px-3 py-2 bg-surface-alt border border-border-subtle rounded-lg text-sm text-text-pri focus:outline-none focus:border-border-main transition-all placeholder:text-text-sec"
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-[11px] font-semibold text-text-ter uppercase tracking-[0.1em] px-1">Priority</label>
                        <button
                            onClick={() => setFilters({ ...filters, hot_only: !filters.hot_only })}
                            className={`flex items-center gap-2 px-4 py-2 text-[11px] uppercase tracking-[0.04em] font-semibold rounded-[20px] border transition-all h-[38px] ${filters.hot_only
                                ? 'bg-priority-hot-bg border-priority-hot-border text-priority-hot-text'
                                : 'bg-surface-alt border-border-subtle text-text-sec hover:bg-surface-hover hover:text-text-pri'
                                }`}
                        >
                            <span className={`h-2 w-2 rounded-full ${filters.hot_only ? 'bg-priority-hot-text' : 'bg-text-sec'}`} />
                            Hot Only (85+)
                        </button>
                    </div>

                    <div className="ml-auto flex items-center gap-2 text-sm text-text-sec bg-surface-alt px-3 py-2 rounded-lg border border-border-subtle">
                        <span className="font-semibold text-text-pri">{stats.count}</span> results found
                    </div>

                </CardContent>
            </Card>

            {/* Results Table */}
            <Card className="border-border-main bg-surface shadow-none overflow-hidden rounded-lg">
                <div className="max-h-[600px] overflow-auto custom-scrollbar">
                    <Table>
                        <TableHeader className="bg-thead-bg sticky top-0 z-10 border-b border-border-subtle">
                            <TableRow className="hover:bg-transparent border-border-subtle">
                                <TableHead className="w-[300px] text-[11px] text-text-ter uppercase tracking-[0.1em] font-semibold">Company</TableHead>
                                <TableHead className="text-[11px] text-text-ter uppercase tracking-[0.1em] font-semibold">Sector</TableHead>
                                <TableHead className="text-[11px] text-text-ter uppercase tracking-[0.1em] font-semibold">Tier</TableHead>
                                <TableHead className="text-right text-[11px] text-text-ter uppercase tracking-[0.1em] font-semibold">Revenue (GBP)</TableHead>
                                <TableHead className="text-right text-[11px] text-text-ter uppercase tracking-[0.1em] font-semibold">Moat Score</TableHead>
                                <TableHead className="text-[11px] text-text-ter uppercase tracking-[0.1em] font-semibold">HQ</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="h-48 text-center text-text-sec">
                                        <div className="flex flex-col items-center gap-3">
                                            <Loader2 className="h-8 w-8 animate-spin text-text-ter" />
                                            <span className="text-sm font-medium">Fetching live data...</span>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ) : data.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="h-48 text-center text-text-sec">
                                        No results match your filters.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                data.map((item) => (
                                    <TableRow key={item.id} className="group hover:bg-surface-hover transition-colors border-border-subtle bg-surface">
                                        <TableCell>
                                            <div>
                                                <div className="text-[14px] font-medium text-text-pri group-hover:text-text-pri transition-colors">{item.name}</div>
                                                <div className="text-[13px] text-text-sec truncate max-w-[250px] mt-0.5">
                                                    {item.moat_analysis?.one_liner || "No summary available"}
                                                </div>
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className="bg-transparent text-text-sec border-border-subtle font-normal rounded-lg">
                                                {item.sector || "Unknown"}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>
                                            <span className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded border bg-surface-alt text-text-sec border-border-subtle`}>
                                                {item.tier ? item.tier.replace('TIER_', '') : '-'}
                                            </span>
                                        </TableCell>
                                        <TableCell className="text-text-pri font-mono text-[14px] text-right">
                                            {item.revenue_gbp
                                                ? `£${(item.revenue_gbp / 1000000).toFixed(1)}m`
                                                : '-'}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <div className="flex flex-col items-end">
                                                <span className={`text-[28px] ${getScoreColor(item.moat_score)}`}>
                                                    {item.moat_score || 0}
                                                </span>
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-text-ter text-[13px]">
                                            {item.hq_country || '-'}
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </div>
            </Card>
        </div>
    );
}
