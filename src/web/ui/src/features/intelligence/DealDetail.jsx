import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { ChevronLeft, Building2, Calendar, Target, Globe, PoundSterling, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function DealDetail() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchDeal = async () => {
            try {
                const res = await fetch(`/api/intelligence/deal/${id}`);
                if (res.ok) {
                    const result = await res.json();
                    setData(result);
                }
            } catch (error) {
                console.error('Failed to fetch deal:', error);
            } finally {
                setLoading(false);
            }
        };
        fetchDeal();
    }, [id]);

    if (loading) {
        return <div className="p-8 text-center text-text-sec">Loading deal details...</div>;
    }

    if (!data) {
        return <div className="p-8 text-center text-text-sec">Deal not found.</div>;
    }

    const { deal, comparables } = data;

    const formatCurrency = (val) => val ? `£${(val / 1000000).toFixed(1)}M` : '—';
    const formatMultiple = (val) => val ? `${val.toFixed(1)}x` : '—';

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <button
                    onClick={() => navigate('/intelligence')}
                    className="flex items-center gap-2 text-sm text-text-sec hover:text-text-pri transition-colors mb-4"
                >
                    <ChevronLeft className="h-4 w-4" />
                    Back to Deals
                </button>
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                    <div>
                        <div className="flex items-center gap-3">
                            <h1 className="text-2xl font-bold text-text-pri">{deal.target_company_name}</h1>
                            <Badge variant="outline" className="text-text-sec border-border-subtle">{deal.deal_type}</Badge>
                        </div>
                        <div className="flex items-center gap-4 mt-2 text-sm text-text-sec">
                            <span className="flex items-center gap-1"><Globe className="h-3 w-3" /> {deal.geography || 'UK'}</span>
                            <span className="flex items-center gap-1"><Building2 className="h-3 w-3" /> {deal.sector}</span>
                            <span className="flex items-center gap-1"><Calendar className="h-3 w-3" /> {deal.deal_date ? new Date(deal.deal_date).toLocaleDateString() : 'Unknown Date'}</span>
                        </div>
                    </div>
                    {deal.confidence_score && (
                        <div className="flex flex-col items-end">
                            <span className="text-xs text-text-sec text-right">Confidence Score</span>
                            <Badge className={cn(
                                "mt-1",
                                deal.confidence_score > 0.8 ? "bg-success/10 text-success" : "bg-warning/10 text-warning"
                            )}>
                                {Math.round(deal.confidence_score * 100)}%
                            </Badge>
                        </div>
                    )}
                </div>
            </div>

            {/* Key Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="bg-surface border-border-subtle">
                    <CardContent className="p-4">
                        <p className="text-xs text-text-sec mb-1 flex items-center gap-1">
                            <PoundSterling className="h-3 w-3" /> Enterprise Value
                        </p>
                        <p className="text-xl font-bold text-text-pri">{formatCurrency(deal.enterprise_value_gbp)}</p>
                    </CardContent>
                </Card>
                <Card className="bg-surface border-border-subtle">
                    <CardContent className="p-4">
                        <p className="text-xs text-text-sec mb-1">Revenue</p>
                        <p className="text-lg font-semibold text-text-pri">{formatCurrency(deal.revenue_gbp)}</p>
                    </CardContent>
                </Card>
                <Card className="bg-surface border-border-subtle">
                    <CardContent className="p-4">
                        <p className="text-xs text-text-sec mb-1">EBITDA</p>
                        <p className="text-lg font-semibold text-text-pri">{formatCurrency(deal.ebitda_gbp)}</p>
                    </CardContent>
                </Card>
                <Card className="bg-surface border-border-subtle">
                    <CardContent className="p-4">
                        <p className="text-xs text-text-sec mb-1 flex items-center gap-1">
                            <TrendingUp className="h-3 w-3" /> EV/EBITDA
                        </p>
                        <p className={cn("text-xl font-bold", deal.ev_ebitda_multiple > 15 ? "text-warning" : "text-primary")}>
                            {formatMultiple(deal.ev_ebitda_multiple)}
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Comparables */}
            <Card className="bg-surface border-border-subtle">
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                        <Target className="h-5 w-5 text-primary" />
                        Comparable Transactions
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="rounded-lg border border-border-subtle overflow-hidden">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-surface-alt">
                                    <TableHead>Target</TableHead>
                                    <TableHead>Date</TableHead>
                                    <TableHead>Similarity</TableHead>
                                    <TableHead className="text-right">EV</TableHead>
                                    <TableHead className="text-right">EV/EBITDA</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {comparables.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={5} className="text-center py-6 text-text-sec">
                                            No comparables found.
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    comparables.map((comp) => (
                                        <TableRow key={comp.id}>
                                            <TableCell className="font-medium text-text-pri">{comp.target_company_name}</TableCell>
                                            <TableCell className="text-text-sec">
                                                {comp.deal_date ? new Date(comp.deal_date).toLocaleDateString() : '—'}
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex flex-col">
                                                    <Badge variant="secondary" className="w-fit mb-1">
                                                        {Math.round(comp.similarity_score * 100)}% Match
                                                    </Badge>
                                                    <span className="text-xs text-text-ter truncate max-w-[200px]">
                                                        {comp.similarity_reasons}
                                                    </span>
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-right font-mono text-text-sec">
                                                {formatCurrency(comp.enterprise_value_gbp)}
                                            </TableCell>
                                            <TableCell className="text-right font-mono font-medium text-text-pri">
                                                {formatMultiple(comp.ev_ebitda_multiple)}
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>
                </CardContent>
            </Card>

            {/* Notes */}
            {deal.notes && (
                <Card className="bg-surface border-border-subtle">
                    <CardHeader>
                        <CardTitle className="text-sm text-text-sec uppercase tracking-wide">Deal Notes</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-text-pri whitespace-pre-line">{deal.notes}</p>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
