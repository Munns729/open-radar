import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Clock } from 'lucide-react';

export default function ConvictionLog({ companyId }) {
    const [entries, setEntries] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!companyId) return;
        let cancelled = false;
        const fetchHistory = async () => {
            setLoading(true);
            try {
                const data = await api.getCanonHistory(companyId, { limit: 50 });
                if (!cancelled) setEntries(Array.isArray(data) ? data : []);
            } catch (e) {
                if (!cancelled) setEntries([]);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        fetchHistory();
        return () => { cancelled = true; };
    }, [companyId]);

    if (loading) {
        return (
            <Card className="border-border-subtle bg-surface">
                <CardContent className="py-6 text-center text-text-sec text-sm">Loading history…</CardContent>
            </Card>
        );
    }

    return (
        <Card className="border-border-subtle bg-surface">
            <CardHeader>
                <CardTitle className="text-lg">Conviction log</CardTitle>
            </CardHeader>
            <CardContent>
                {entries.length === 0 ? (
                    <p className="text-center text-text-ter text-sm py-6">No canon changes yet.</p>
                ) : (
                    <div className="space-y-4 relative before:absolute before:inset-0 before:ml-4 before:-translate-x-px before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-border-subtle before:to-transparent">
                        {entries.map((entry) => (
                            <div key={entry.id} className="relative flex gap-3 pl-2">
                                <div className="flex items-center justify-center w-8 h-8 rounded-full border border-border bg-surface shrink-0">
                                    <Clock className="w-4 h-4 text-text-ter" />
                                </div>
                                <div className="flex-1 min-w-0 pb-4">
                                    <div className="flex flex-wrap items-center gap-2 mb-1">
                                        <Badge variant="secondary" className="text-xs">
                                            {entry.field_changed}
                                        </Badge>
                                        {entry.source_module && (
                                            <Badge variant="outline" className="text-xs">
                                                {entry.source_module}
                                            </Badge>
                                        )}
                                        <time className="text-xs text-text-ter">
                                            {entry.created_at ? new Date(entry.created_at).toLocaleString() : ''}
                                        </time>
                                    </div>
                                    <div className="text-sm text-text-sec">
                                        {entry.previous_value != null && entry.previous_value !== '' && (
                                            <span className="line-through text-text-ter">{entry.previous_value}</span>
                                        )}
                                        {entry.previous_value != null && entry.previous_value !== '' && entry.new_value && ' → '}
                                        {entry.new_value && (
                                            <span className="text-text-pri">{entry.new_value}</span>
                                        )}
                                        {!entry.previous_value && !entry.new_value && '—'}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
