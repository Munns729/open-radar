import React, { useEffect, useState, useMemo } from 'react';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';

export default function CoverageManifest() {
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        const fetchCoverage = async () => {
            setLoading(true);
            try {
                const data = await api.getCanonCoverage();
                if (!cancelled) setRows(Array.isArray(data) ? data : []);
            } catch (e) {
                if (!cancelled) setRows([]);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        fetchCoverage();
        return () => { cancelled = true; };
    }, []);

    const sortedRows = useMemo(() => {
        if (!rows.length) return [];
        return [...rows].sort((a, b) => (b.stale_count ?? 0) - (a.stale_count ?? 0));
    }, [rows]);

    const formatTierBreakdown = (tb) => {
        if (!tb || typeof tb !== 'object') return '—';
        const parts = ['1A', '1B', '2', 'waitlist']
            .filter((k) => tb[k] != null && tb[k] !== 0)
            .map((k) => `${k}: ${tb[k]}`);
        return parts.length ? parts.join(', ') : '—';
    };

    const formatLastActivity = (iso) => {
        if (!iso) return '—';
        try {
            const d = new Date(iso);
            return d.toLocaleDateString(undefined, { dateStyle: 'short' });
        } catch {
            return iso;
        }
    };

    return (
        <Card className="border-border-subtle bg-surface">
            <CardHeader className="pb-2">
                <CardTitle className="text-lg">Coverage by sector</CardTitle>
                <p className="text-xs text-text-sec">
                    Canon coverage and staleness by sector. Stale = not refreshed in 90+ days.
                </p>
            </CardHeader>
            <CardContent>
                <div className="rounded-lg border border-border-subtle overflow-hidden">
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-surface-alt hover:bg-surface-alt">
                                <TableHead className="text-text-ter">Sector</TableHead>
                                <TableHead className="text-text-ter text-right">Companies</TableHead>
                                <TableHead className="text-text-ter text-right">Active</TableHead>
                                <TableHead className="text-text-ter text-right">Stale</TableHead>
                                <TableHead className="text-text-ter">Tier breakdown</TableHead>
                                <TableHead className="text-text-ter">Last activity</TableHead>
                                <TableHead className="text-text-ter text-right">Signals (30d)</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={7} className="text-center py-8 text-text-sec text-sm">
                                        Loading coverage…
                                    </TableCell>
                                </TableRow>
                            ) : sortedRows.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={7} className="text-center py-8 text-text-sec text-sm">
                                        No coverage data. Canon records will appear after companies are processed.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                sortedRows.map((row) => (
                                    <TableRow key={row.sector ?? 'Unknown'} className="hover:bg-surface-hover">
                                        <TableCell className="font-medium text-text-pri">
                                            {row.sector ?? 'Unknown'}
                                        </TableCell>
                                        <TableCell className="text-right">{row.company_count ?? 0}</TableCell>
                                        <TableCell className="text-right">{row.active_count ?? 0}</TableCell>
                                        <TableCell
                                            className={`text-right font-medium ${(row.stale_count ?? 0) > 0 ? 'bg-amber-500/15 text-amber-700 dark:text-amber-400' : ''}`}
                                        >
                                            {row.stale_count ?? 0}
                                        </TableCell>
                                        <TableCell className="text-sm text-text-sec">
                                            {formatTierBreakdown(row.tier_breakdown)}
                                        </TableCell>
                                        <TableCell className="text-sm text-text-sec whitespace-nowrap">
                                            {formatLastActivity(row.last_activity)}
                                        </TableCell>
                                        <TableCell className="text-right">{row.recent_signal_count ?? 0}</TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </div>
            </CardContent>
        </Card>
    );
}
