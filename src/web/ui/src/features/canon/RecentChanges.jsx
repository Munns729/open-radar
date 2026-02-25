import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { ChevronRight } from 'lucide-react';

export default function RecentChanges() {
    const navigate = useNavigate();
    const [entries, setEntries] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        const fetchRecent = async () => {
            setLoading(true);
            try {
                const data = await api.getCanonRecentChanges({ limit: 20 });
                if (!cancelled) setEntries(Array.isArray(data) ? data : []);
            } catch (e) {
                if (!cancelled) setEntries([]);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        fetchRecent();
        return () => { cancelled = true; };
    }, []);

    const changeSummary = (entry) => {
        const oldVal = entry.previous_value ?? '';
        const newVal = entry.new_value ?? '';
        if (oldVal && newVal) return `${oldVal.slice(0, 30)}… → ${newVal.slice(0, 30)}…`;
        if (newVal) return newVal.slice(0, 60) + (newVal.length > 60 ? '…' : '');
        return '—';
    };

    return (
        <Card className="border-border-subtle bg-surface">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-lg">Recent canon changes</CardTitle>
                <button
                    onClick={() => navigate('/tracker')}
                    className="text-xs text-primary hover:text-primary-light flex items-center gap-1"
                >
                    Tracker <ChevronRight className="h-3 w-3" />
                </button>
            </CardHeader>
            <CardContent>
                <div className="rounded-lg border border-border-subtle overflow-hidden">
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-surface-alt hover:bg-surface-alt">
                                <TableHead className="text-text-ter">Company ID</TableHead>
                                <TableHead className="text-text-ter">Field</TableHead>
                                <TableHead className="text-text-ter">Change</TableHead>
                                <TableHead className="text-text-ter">Time</TableHead>
                                <TableHead className="w-8" />
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={5} className="text-center py-8 text-text-sec text-sm">
                                        Loading…
                                    </TableCell>
                                </TableRow>
                            ) : entries.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={5} className="text-center py-8 text-text-sec text-sm">
                                        No recent changes
                                    </TableCell>
                                </TableRow>
                            ) : (
                                entries.map((entry) => (
                                    <TableRow
                                        key={entry.id}
                                        className="cursor-pointer hover:bg-surface-hover transition-colors"
                                        onClick={() => navigate(`/tracker?company=${entry.company_id}`)}
                                    >
                                        <TableCell className="font-mono text-sm">{entry.company_id}</TableCell>
                                        <TableCell className="text-sm">{entry.field_changed}</TableCell>
                                        <TableCell className="text-sm text-text-sec max-w-[200px] truncate" title={changeSummary(entry)}>
                                            {changeSummary(entry)}
                                        </TableCell>
                                        <TableCell className="text-xs text-text-ter whitespace-nowrap">
                                            {entry.created_at ? new Date(entry.created_at).toLocaleString() : '—'}
                                        </TableCell>
                                        <TableCell>
                                            <ChevronRight className="h-4 w-4 text-text-ter" />
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
