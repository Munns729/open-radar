import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { useCurrency } from '@/context/CurrencyContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Download, Split } from 'lucide-react';

export default function CarveoutBoard() {
    const { convert, currency } = useCurrency();
    const [targets, setTargets] = useState([]);
    const [loading, setLoading] = useState(true);

    // Helper to format large numbers with currency conversion
    const formatMoney = (amount) => {
        if (!amount) return '—';
        // Revenue comes in as EUR from the API (revenue_eur)
        const converted = convert(amount, 'EUR');
        const symbol = currency === 'USD' ? '$' : currency === 'EUR' ? '€' : '£';
        return `${symbol}${(converted / 1000000).toFixed(1)}M`;
    };

    useEffect(() => {
        const fetchTargets = async () => {
            try {
                const data = await api.getCarveoutTargets();
                setTargets(data || []);
            } catch (error) {
                console.error("Failed to fetch carveout targets", error);
            } finally {
                setLoading(false);
            }
        };
        fetchTargets();
    }, []);

    const handleExport = () => {
        window.open(api.getCarveoutExportUrl(), '_blank');
    };

    return (
        <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl">
            <CardHeader className="flex flex-row items-center justify-between">
                <div>
                    <CardTitle className="flex items-center gap-2">
                        <Split className="h-5 w-5 text-orange-400" />
                        Carveout Scanner
                    </CardTitle>
                    <CardDescription>Potential corporate divestiture candidates.</CardDescription>
                </div>
                <Button onClick={handleExport} className="gap-2 bg-orange-600 hover:bg-orange-700">
                    <Download className="h-4 w-4" /> Export CSV
                </Button>
            </CardHeader>
            <CardContent>
                <div className="rounded-md border border-border/50 bg-background/50">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Division</TableHead>
                                <TableHead>Parent Company</TableHead>
                                <TableHead>Probability</TableHead>
                                <TableHead>Attractiveness</TableHead>
                                <TableHead>Timeline</TableHead>
                                <TableHead>Est. Revenue</TableHead>
                                <TableHead>Autonomy</TableHead>
                                <TableHead>Status</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="text-center h-24 text-muted-foreground">Loading targets...</TableCell>
                                </TableRow>
                            ) : targets.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="text-center h-24 text-muted-foreground">No high-probability targets found.</TableCell>
                                </TableRow>
                            ) : (
                                targets.map((t) => (
                                    <TableRow key={t.id} className="hover:bg-orange-950/10">
                                        <TableCell className="font-medium text-orange-200">{t.division_name}</TableCell>
                                        <TableCell>{t.parent_name}</TableCell>
                                        <TableCell>
                                            <div className="flex items-center gap-2">
                                                <div className="h-2 w-16 bg-secondary rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full bg-orange-500"
                                                        style={{ width: `${t.probability}%` }}
                                                    />
                                                </div>
                                                <span className="text-xs">{t.probability}%</span>
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            <span className={`font-bold ${(t.attractiveness_score || 0) >= 80 ? 'text-emerald-400' : 'text-muted-foreground'}`}>
                                                {t.attractiveness_score || '-'}
                                            </span>
                                        </TableCell>
                                        <TableCell>{t.timeline}</TableCell>
                                        <TableCell>{formatMoney(t.revenue)}</TableCell>
                                        <TableCell>
                                            <div className="flex flex-col text-xs">
                                                <span className="text-muted-foreground capitalize">{t.autonomy_level || '-'}</span>
                                                <span className="text-[10px] text-orange-400 capitalize">{t.strategic_autonomy}</span>
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className="border-orange-500/50 text-orange-400">
                                                {t.status}
                                            </Badge>
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
