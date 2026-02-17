import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/Table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input'; // Assuming Input exists, if not I'll use standard input
import { Search, Filter, ArrowRight, TrendingUp } from 'lucide-react';

export default function DealTable() {
    const navigate = useNavigate();
    const [deals, setDeals] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({
        sector: '',
        dealType: '',
        minValue: ''
    });

    useEffect(() => {
        const fetchDeals = async () => {
            setLoading(true);
            try {
                const params = new URLSearchParams();
                if (filters.sector) params.append('sector', filters.sector);
                if (filters.dealType) params.append('deal_type', filters.dealType);
                if (filters.minValue) params.append('min_value', filters.minValue);

                const res = await fetch(`/api/intelligence/deals?${params.toString()}`);
                if (res.ok) {
                    const data = await res.json();
                    setDeals(data);
                }
            } catch (error) {
                console.error('Failed to fetch deals:', error);
            } finally {
                setLoading(false);
            }
        };

        const timeout = setTimeout(fetchDeals, 500); // Debounce
        return () => clearTimeout(timeout);
    }, [filters]);

    const formatCurrency = (val) => {
        if (!val) return '—';
        return `£${(val / 1000000).toFixed(1)}M`;
    };

    const formatMultiple = (val) => {
        if (!val) return '—';
        return `${val.toFixed(1)}x`;
    };

    return (
        <Card className="border-border-subtle bg-surface shadow-sm">
            <CardHeader className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0 pb-4">
                <CardTitle className="text-lg flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-primary" />
                    Deal Records
                </CardTitle>

                <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
                    {/* Filters */}
                    <div className="relative">
                        <select
                            className="h-9 rounded-md border border-border-subtle bg-surface-alt px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                            value={filters.sector}
                            onChange={(e) => setFilters({ ...filters, sector: e.target.value })}
                        >
                            <option value="">All Sectors</option>
                            <option value="TMT">TMT</option>
                            <option value="Healthcare">Healthcare</option>
                            <option value="Industrial">Industrial</option>
                            <option value="Consumer">Consumer</option>
                            <option value="Services">Services</option>
                        </select>
                    </div>

                    <div className="relative">
                        <select
                            className="h-9 rounded-md border border-border-subtle bg-surface-alt px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                            value={filters.dealType}
                            onChange={(e) => setFilters({ ...filters, dealType: e.target.value })}
                        >
                            <option value="">All Types</option>
                            <option value="Buyout">Buyout</option>
                            <option value="Growth">Growth</option>
                            <option value="Carveout">Carveout</option>
                            <option value="Secondary">Secondary</option>
                        </select>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="rounded-lg border border-border-subtle overflow-hidden">
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-surface-alt hover:bg-surface-alt">
                                <TableHead className="w-[120px]">Date</TableHead>
                                <TableHead>Target Company</TableHead>
                                <TableHead>Type</TableHead>
                                <TableHead>Sector</TableHead>
                                <TableHead className="text-right">Enterprise Value</TableHead>
                                <TableHead className="text-right">EV/EBITDA</TableHead>
                                <TableHead className="w-[50px]"></TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={7} className="text-center py-8 text-text-sec">
                                        Loading deals...
                                    </TableCell>
                                </TableRow>
                            ) : deals.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={7} className="text-center py-8 text-text-sec">
                                        No deals found matching your criteria.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                deals.map((deal) => (
                                    <TableRow
                                        key={deal.id}
                                        onClick={() => navigate(`/intelligence/${deal.id}`)}
                                        className="cursor-pointer hover:bg-surface-hover transition-colors"
                                    >
                                        <TableCell className="font-medium text-text-sec">
                                            {deal.deal_date ? new Date(deal.deal_date).toLocaleDateString() : '—'}
                                        </TableCell>
                                        <TableCell>
                                            <div className="font-semibold text-text-pri">{deal.target_company_name}</div>
                                            <div className="text-xs text-text-ter">{deal.geography || 'UK'}</div>
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className="bg-surface-alt text-text-sec border-border-subtle">
                                                {deal.deal_type}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="secondary" className="bg-primary/10 text-primary hover:bg-primary/20">
                                                {deal.sector}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-right font-mono text-text-pri">
                                            {formatCurrency(deal.enterprise_value_gbp)}
                                        </TableCell>
                                        <TableCell className="text-right font-mono">
                                            <span className={deal.ev_ebitda_multiple > 15 ? 'text-warning font-bold' : 'text-text-sec'}>
                                                {formatMultiple(deal.ev_ebitda_multiple)}
                                            </span>
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
    );
}
