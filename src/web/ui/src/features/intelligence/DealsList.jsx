import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Download, Search, Filter, TrendingUp, Building2 } from 'lucide-react';
import { motion } from 'framer-motion';

export default function DealsList() {
    const [deals, setDeals] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [filters, setFilters] = useState({
        sector: '',
        dealType: '',
        minValue: '',
        maxValue: ''
    });

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                let url = '/api/intelligence/deals?limit=50';
                if (filters.sector) url += `&sector=${filters.sector}`;
                if (filters.dealType) url += `&deal_type=${filters.dealType}`;
                if (filters.minValue) url += `&min_value=${filters.minValue}`;
                if (filters.maxValue) url += `&max_value=${filters.maxValue}`;

                const res = await fetch(url);
                const data = await res.json();
                setDeals(data);
            } catch (error) {
                console.error("Failed to fetch deals", error);
            } finally {
                setLoading(false);
            }
        };

        const debounce = setTimeout(fetchData, 300);
        return () => clearTimeout(debounce);
    }, [filters]);

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

    const getDealTypeBadge = (type) => {
        const colors = {
            buyout: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
            growth: 'bg-green-500/20 text-green-300 border-green-500/30',
            carveout: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
            secondary: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
            recap: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
            add_on: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
        };
        return colors[type] || 'bg-slate-500/20 text-slate-300';
    };

    const filteredDeals = deals.filter(deal =>
        deal.target_company_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        deal.sector?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className="space-y-6">
            <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                    <div>
                        <CardTitle className="text-xl flex items-center gap-2">
                            <Building2 className="h-5 w-5 text-indigo-400" />
                            PE Deal Activity
                        </CardTitle>
                        <CardDescription>Recent private equity transactions and valuations.</CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="relative">
                            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                            <input
                                type="search"
                                placeholder="Search deals..."
                                className="h-10 w-[200px] rounded-lg border border-input bg-background pl-9 pr-4 text-sm outline-none focus:ring-1 focus:ring-ring"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </div>
                        <select
                            className="h-10 rounded-lg border border-input bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
                            value={filters.sector}
                            onChange={(e) => setFilters({ ...filters, sector: e.target.value })}
                        >
                            <option value="">All Sectors</option>
                            <option value="Technology">Technology</option>
                            <option value="Healthcare">Healthcare</option>
                            <option value="Industrial">Industrial</option>
                            <option value="Financial Services">Financial Services</option>
                            <option value="Consumer">Consumer</option>
                        </select>
                        <select
                            className="h-10 rounded-lg border border-input bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
                            value={filters.dealType}
                            onChange={(e) => setFilters({ ...filters, dealType: e.target.value })}
                        >
                            <option value="">All Types</option>
                            <option value="buyout">Buyout</option>
                            <option value="growth">Growth</option>
                            <option value="carveout">Carveout</option>
                            <option value="secondary">Secondary</option>
                        </select>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="rounded-md border border-border/50 bg-background/50 overflow-hidden">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead className="w-[200px]">Target</TableHead>
                                    <TableHead>Date</TableHead>
                                    <TableHead>Type</TableHead>
                                    <TableHead>Sector</TableHead>
                                    <TableHead className="text-right">EV</TableHead>
                                    <TableHead className="text-right">EV/EBITDA</TableHead>
                                    <TableHead className="text-right">EV/Rev</TableHead>
                                    <TableHead className="text-center">Confidence</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    <TableRow>
                                        <TableCell colSpan={8} className="text-center h-24 text-muted-foreground">
                                            Loading deals...
                                        </TableCell>
                                    </TableRow>
                                ) : filteredDeals.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={8} className="text-center h-24 text-muted-foreground">
                                            No deals found matching criteria.
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    filteredDeals.map((deal, idx) => (
                                        <motion.tr
                                            key={deal.id || idx}
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: idx * 0.03 }}
                                            className="group cursor-pointer hover:bg-indigo-950/20 border-b border-border/30"
                                        >
                                            <TableCell>
                                                <div className="font-medium text-indigo-200">{deal.target_company_name}</div>
                                                <div className="text-xs text-muted-foreground">{deal.geography}</div>
                                            </TableCell>
                                            <TableCell className="text-sm text-muted-foreground">
                                                {deal.deal_date || '-'}
                                            </TableCell>
                                            <TableCell>
                                                <Badge className={`${getDealTypeBadge(deal.deal_type)} text-xs`}>
                                                    {deal.deal_type || 'Unknown'}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-sm">{deal.sector || '-'}</TableCell>
                                            <TableCell className="text-right font-medium text-emerald-400">
                                                {formatGBP(deal.enterprise_value_gbp)}
                                            </TableCell>
                                            <TableCell className="text-right">
                                                {formatMultiple(deal.ev_ebitda_multiple)}
                                            </TableCell>
                                            <TableCell className="text-right">
                                                {formatMultiple(deal.ev_revenue_multiple)}
                                            </TableCell>
                                            <TableCell className="text-center">
                                                <div className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-xs font-medium
                                                    ${deal.confidence_score >= 80 ? 'bg-green-500/20 text-green-400' :
                                                        deal.confidence_score >= 60 ? 'bg-yellow-500/20 text-yellow-400' :
                                                            'bg-slate-500/20 text-slate-400'}`}>
                                                    {deal.confidence_score || '-'}
                                                </div>
                                            </TableCell>
                                        </motion.tr>
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
