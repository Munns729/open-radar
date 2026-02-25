import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Check, AlertTriangle } from 'lucide-react';

export default function ResilienceFlagsFeed() {
    const [flags, setFlags] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchFlags = async () => {
        try {
            const res = await api.getResilienceFlags({ reviewed: false });
            setFlags(Array.isArray(res) ? res : []);
        } catch {
            setFlags([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchFlags();
    }, []);

    const handleMarkReviewed = async (flagId) => {
        try {
            await api.markResilienceFlagReviewed(flagId);
            setFlags((prev) => prev.filter((f) => f.id !== flagId));
        } catch (e) {
            console.error('Mark reviewed failed', e);
        }
    };

    if (loading) {
        return (
            <div className="p-6 text-center text-text-sec text-sm">
                Loading flags...
            </div>
        );
    }

    return (
        <Card className="border-border-subtle">
            <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                    AI Resilience Flags (unreviewed)
                </CardTitle>
            </CardHeader>
            <CardContent>
                <ul className="space-y-3">
                    {flags.map((f) => (
                        <li
                            key={f.id}
                            className="flex items-center justify-between gap-4 p-3 rounded-lg bg-surface-alt border border-border-subtle"
                        >
                            <div className="min-w-0">
                                <span className="font-medium text-text-pri">Company {f.company_id}</span>
                                <span className="text-text-ter mx-2">·</span>
                                <span className="text-text-sec">L{f.capability_level}</span>
                                <div className="text-xs text-text-sec mt-0.5">
                                    {f.previous_verdict ?? '—'} → <strong className="text-text-pri">{f.new_verdict}</strong>
                                    {f.composite_delta != null && (
                                        <span className="ml-2">
                                            (Δ{f.composite_delta >= 0 ? '+' : ''}{f.composite_delta.toFixed(1)})
                                        </span>
                                    )}
                                </div>
                            </div>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleMarkReviewed(f.id)}
                            >
                                <Check className="h-3.5 w-3.5 mr-1" />
                                Mark Reviewed
                            </Button>
                        </li>
                    ))}
                </ul>
                {flags.length === 0 && (
                    <p className="py-6 text-center text-text-ter text-sm">No unreviewed flags.</p>
                )}
            </CardContent>
        </Card>
    );
}
