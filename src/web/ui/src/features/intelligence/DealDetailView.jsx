import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ArrowLeft, Building2, TrendingUp, Scale, ExternalLink } from 'lucide-react';
import { motion } from 'framer-motion';

export default function DealDetailView({ dealId, onBack }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            if (!dealId) return;
            setLoading(true);
            try {
                const res = await fetch(`/api/intelligence/deal/${dealId}`);
                const json = await res.json();
                setData(json);
            } catch (error) {
                console.error("Failed to fetch deal details", error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [dealId]);

    const formatGBP = (value) => {
        if (!value) return '-';
        if (value >= 1000000000) return `£${(value / 1000000000).toFixed(1)}B`;
        if (value >= 1000000) return `£${(value / 1000000).toFixed(1)}M`;
        return `£${value.toLocaleString()}`;
    };

    const formatMultiple = (value) => {
        if (!value) return '-';
        return `${value.toFixed(1)}x`;
    };

    if (loading) {
        return (
            <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl">
                <CardContent className="flex items-center justify-center h-48">
                    <div className="text-muted-foreground">Loading deal details...</div>
                </CardContent>
            </Card>
        );
    }

    if (!data || !data.deal) {
        return (
            <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl">
                <CardContent className="flex items-center justify-center h-48">
                    <div className="text-muted-foreground">Deal not found</div>
                </CardContent>
            </Card>
        );
    }

    const { deal, comparables } = data;

    return (
        <div className="space-y-6">
            {/* Header with Back Button */}
            {onBack && (
                <Button variant="ghost" onClick={onBack} className="gap-2 text-muted-foreground hover:text-foreground">
                    <ArrowLeft className="h-4 w-4" />
                    Back to Deals
                </Button>
            )}

            {/* Deal Summary Card */}
            <Card className="border-border/50 bg-gradient-to-br from-indigo-950/50 to-purple-950/30 backdrop-blur-xl shadow-2xl">
                <CardHeader>
                    <div className="flex items-start justify-between">
                        <div>
                            <CardTitle className="text-2xl flex items-center gap-3">
                                <Building2 className="h-6 w-6 text-indigo-400" />
                                {deal.target_company_name}
                            </CardTitle>
                            <CardDescription className="mt-2">
                                {deal.sector} • {deal.geography} • {deal.deal_date}
                            </CardDescription>
                        </div>
                        <Badge className="bg-purple-500/20 text-purple-300 border-purple-500/30 text-sm px-3 py-1">
                            {deal.deal_type?.toUpperCase()}
                        </Badge>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                        <div className="bg-slate-900/50 rounded-lg p-4 border border-border/30">
                            <div className="text-xs text-muted-foreground uppercase tracking-wider">Enterprise Value</div>
                            <div className="text-2xl font-bold text-emerald-400 mt-1">
                                {formatGBP(deal.enterprise_value_gbp)}
                            </div>
                        </div>
                        <div className="bg-slate-900/50 rounded-lg p-4 border border-border/30">
                            <div className="text-xs text-muted-foreground uppercase tracking-wider">EV/EBITDA</div>
                            <div className="text-2xl font-bold text-blue-400 mt-1">
                                {formatMultiple(deal.ev_ebitda_multiple)}
                            </div>
                        </div>
                        <div className="bg-slate-900/50 rounded-lg p-4 border border-border/30">
                            <div className="text-xs text-muted-foreground uppercase tracking-wider">EV/Revenue</div>
                            <div className="text-2xl font-bold text-purple-400 mt-1">
                                {formatMultiple(deal.ev_revenue_multiple)}
                            </div>
                        </div>
                        <div className="bg-slate-900/50 rounded-lg p-4 border border-border/30">
                            <div className="text-xs text-muted-foreground uppercase tracking-wider">Revenue</div>
                            <div className="text-2xl font-bold text-amber-400 mt-1">
                                {formatGBP(deal.revenue_gbp)}
                            </div>
                        </div>
                    </div>

                    {/* Additional Details */}
                    <div className="mt-6 grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                        <div>
                            <span className="text-muted-foreground">EBITDA:</span>
                            <span className="ml-2 text-foreground">{formatGBP(deal.ebitda_gbp)}</span>
                        </div>
                        <div>
                            <span className="text-muted-foreground">Equity:</span>
                            <span className="ml-2 text-foreground">{formatGBP(deal.equity_investment_gbp)}</span>
                        </div>
                        <div>
                            <span className="text-muted-foreground">Debt:</span>
                            <span className="ml-2 text-foreground">{formatGBP(deal.debt_gbp)}</span>
                        </div>
                        <div>
                            <span className="text-muted-foreground">Source:</span>
                            <span className="ml-2 text-foreground capitalize">{deal.source}</span>
                        </div>
                        <div>
                            <span className="text-muted-foreground">Confidence:</span>
                            <span className={`ml-2 ${deal.confidence_score >= 70 ? 'text-green-400' : 'text-yellow-400'}`}>
                                {deal.confidence_score}%
                            </span>
                        </div>
                        {deal.source_url && (
                            <div>
                                <a href={deal.source_url} target="_blank" rel="noopener noreferrer"
                                    className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
                                    View Source <ExternalLink className="h-3 w-3" />
                                </a>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Comparables Table */}
            <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl">
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                        <Scale className="h-5 w-5 text-indigo-400" />
                        Comparable Transactions
                    </CardTitle>
                    <CardDescription>
                        Similar deals based on sector, size, and geography.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {comparables && comparables.length > 0 ? (
                        <div className="rounded-md border border-border/50 bg-background/50 overflow-hidden">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Target</TableHead>
                                        <TableHead>Date</TableHead>
                                        <TableHead>Sector</TableHead>
                                        <TableHead className="text-right">EV</TableHead>
                                        <TableHead className="text-right">EV/EBITDA</TableHead>
                                        <TableHead className="text-right">EV/Rev</TableHead>
                                        <TableHead className="text-center">Similarity</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {comparables.map((comp, idx) => (
                                        <motion.tr
                                            key={comp.id || idx}
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            transition={{ delay: idx * 0.05 }}
                                            className="hover:bg-indigo-950/20 border-b border-border/30"
                                        >
                                            <TableCell className="font-medium text-indigo-200">
                                                {comp.target_company_name}
                                            </TableCell>
                                            <TableCell className="text-sm text-muted-foreground">
                                                {comp.deal_date || '-'}
                                            </TableCell>
                                            <TableCell className="text-sm">{comp.sector || '-'}</TableCell>
                                            <TableCell className="text-right font-medium">
                                                {formatGBP(comp.enterprise_value_gbp)}
                                            </TableCell>
                                            <TableCell className="text-right">
                                                {formatMultiple(comp.ev_ebitda_multiple)}
                                            </TableCell>
                                            <TableCell className="text-right">
                                                {formatMultiple(comp.ev_revenue_multiple)}
                                            </TableCell>
                                            <TableCell className="text-center">
                                                <div className={`inline-flex items-center justify-center px-2 py-1 rounded text-xs font-medium
                                                    ${comp.similarity_score >= 80 ? 'bg-green-500/20 text-green-400' :
                                                        comp.similarity_score >= 60 ? 'bg-yellow-500/20 text-yellow-400' :
                                                            'bg-slate-500/20 text-slate-400'}`}>
                                                    {comp.similarity_score}%
                                                </div>
                                            </TableCell>
                                        </motion.tr>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>
                    ) : (
                        <div className="text-center py-8 text-muted-foreground">
                            No comparable transactions found.
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
