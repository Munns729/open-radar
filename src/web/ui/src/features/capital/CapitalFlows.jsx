import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Banknote, ArrowRight } from 'lucide-react';

export default function CapitalFlows() {
    const [investments, setInvestments] = useState([]);
    const [stats, setStats] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [invData, statsData] = await Promise.all([
                    api.getInvestments(),
                    api.getCapitalStats()
                ]);

                setInvestments(invData || []);
                setStats(statsData || []);
            } catch (error) {
                console.error("Failed to fetch data", error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    // Filter for key UK firms to highlight
    const ukFirms = stats.filter(s => ["Inflexion", "Synova", "Mayfair Equity Partners"].includes(s.firm));

    return (
        <div className="space-y-6">
            {/* Stats Overview */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {ukFirms.map(firm => (
                    <Card key={firm.firm} className="border-border/50 bg-card/60 backdrop-blur-xl group hover:bg-card/80 transition-all">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-lg font-medium text-emerald-100 flex justify-between">
                                {firm.firm}
                                <span className="text-xs bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-500/20">
                                    {firm.total_companies} Portcos
                                </span>
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {/* Coverage Bar */}
                                <div>
                                    <div className="flex justify-between text-xs mb-1">
                                        <span className="text-muted-foreground">Enrichment Coverage</span>
                                        <span className="text-emerald-400">{firm.coverage_pct}%</span>
                                    </div>
                                    <div className="w-full bg-gray-700 rounded-full h-1.5 overflow-hidden">
                                        <div
                                            className="bg-emerald-500 h-1.5 rounded-full"
                                            style={{ width: `${firm.coverage_pct}%` }}
                                        ></div>
                                    </div>
                                </div>

                                {/* Themes & Moats */}
                                <div className="grid grid-cols-2 gap-2 text-xs">
                                    <div>
                                        <span className="text-gray-500 block mb-1 uppercase tracking-wider text-[10px]">Top Themes</span>
                                        <div className="flex flex-wrap gap-1">
                                            {firm.top_themes.length > 0 ? firm.top_themes.map(t => (
                                                <span key={t} className="bg-blue-900/30 text-blue-200 px-1.5 py-0.5 rounded border border-blue-500/10 line-clamp-1">
                                                    {t}
                                                </span>
                                            )) : <span className="text-gray-600">-</span>}
                                        </div>
                                    </div>
                                    <div>
                                        <span className="text-gray-500 block mb-1 uppercase tracking-wider text-[10px]">Identified Moats</span>
                                        <div className="flex flex-wrap gap-1">
                                            {firm.top_moats.length > 0 ? firm.top_moats.map(m => (
                                                <span key={m} className="bg-purple-900/30 text-purple-200 px-1.5 py-0.5 rounded border border-purple-500/10 line-clamp-1">
                                                    {m}
                                                </span>
                                            )) : <span className="text-gray-600">-</span>}
                                        </div>
                                    </div>
                                </div>

                                {/* Deal Size */}
                                {firm.avg_deal_size_usd > 0 && (
                                    <div className="pt-2 border-t border-border/50 flex justify-between items-center text-xs">
                                        <span className="text-muted-foreground">Avg. Valuation</span>
                                        <span className="font-semibold text-emerald-300">
                                            ${(firm.avg_deal_size_usd / 1000000).toFixed(1)}M
                                        </span>
                                    </div>
                                )}

                                {/* Moat Returns */}
                                {firm.returns_by_moat && firm.returns_by_moat.length > 0 && (
                                    <div className="pt-2 border-t border-border/50">
                                        <span className="text-xs text-muted-foreground block mb-1">Avg MOIC by Moat</span>
                                        <div className="space-y-1">
                                            {firm.returns_by_moat.slice(0, 2).map(r => (
                                                <div key={r.moat} className="flex justify-between items-center text-xs">
                                                    <span className="text-gray-300">{r.moat}</span>
                                                    <span className="font-mono text-emerald-400 bg-emerald-950/40 px-1 rounded">
                                                        {r.avg_moic}x
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Banknote className="h-5 w-5 text-emerald-400" />
                        Capital Flows - Investment Feed
                    </CardTitle>
                    <CardDescription>Recent tracked investments and enrichment status.</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="rounded-md border border-border/50 bg-background/50">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Target Company</TableHead>
                                    <TableHead>Investor</TableHead>
                                    <TableHead className="w-[40%]">Investment Thesis (Extracted)</TableHead>
                                    <TableHead>Sector</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    <TableRow>
                                        <TableCell colSpan={4} className="text-center h-24 text-muted-foreground">Loading investments...</TableCell>
                                    </TableRow>
                                ) : investments.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={4} className="text-center h-24 text-muted-foreground">No recent investments recorded.</TableCell>
                                    </TableRow>
                                ) : (
                                    investments.map((inv) => (
                                        <TableRow key={inv.id} className="hover:bg-emerald-950/10">
                                            <TableCell className="font-medium text-foreground">{inv.target}</TableCell>
                                            <TableCell className="font-medium text-emerald-200">{inv.investor}</TableCell>
                                            <TableCell className="text-sm text-muted-foreground">
                                                {inv.thesis ? (
                                                    <span className="text-emerald-100/90">{inv.thesis}</span>
                                                ) : (
                                                    <span className="text-gray-600 italic">Pending enrichment...</span>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                <span className="inline-flex items-center rounded-md bg-muted px-2 py-1 text-xs font-medium text-muted-foreground ring-1 ring-inset ring-gray-500/10">
                                                    {inv.sector || "Unknown"}
                                                </span>
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
