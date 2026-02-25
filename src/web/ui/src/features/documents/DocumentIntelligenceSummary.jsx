import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { FileText, AlertTriangle, HelpCircle, Shield, TrendingUp } from 'lucide-react';

export default function DocumentIntelligenceSummary({ companyId }) {
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!companyId) return;
        let cancelled = false;
        (async () => {
            setLoading(true);
            setError(null);
            try {
                const data = await api.getDocumentIntelligenceSummary(companyId);
                if (!cancelled) setSummary(data);
            } catch (e) {
                if (!cancelled) setError(e.message || 'Failed to load summary.');
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => { cancelled = true; };
    }, [companyId]);

    if (!companyId) return null;
    if (loading) return <div className="text-text-sec text-sm p-4">Loading summary…</div>;
    if (error) return <div className="text-danger text-sm p-4">{error}</div>;
    if (!summary) return <div className="text-text-sec text-sm p-4">No document intelligence yet.</div>;

    const {
        doc_count_by_type = {},
        red_flags = [],
        open_questions = [],
        moat_evidence_by_pillar = {},
        tier_signals = [],
        proposal_count = 0,
    } = summary;

    const docCount = Object.values(doc_count_by_type).reduce((a, b) => a + b, 0);
    if (docCount === 0) {
        return (
            <Card className="bg-surface border-border-subtle">
                <CardContent className="py-6 text-center text-text-sec">
                    <FileText className="h-10 w-10 mx-auto mb-2 opacity-50" />
                    <p>Upload documents to see intelligence summary.</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="bg-surface border-border-subtle">
            <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                    <FileText className="h-5 w-5" />
                    Document intelligence summary
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="text-sm text-text-sec">
                    Documents by type: {Object.entries(doc_count_by_type).map(([t, n]) => `${t}: ${n}`).join(', ')}
                    {proposal_count > 0 && (
                        <span className="ml-2 text-primary">
                            · {proposal_count} proposal(s) generated
                        </span>
                    )}
                </div>

                {red_flags.length > 0 && (
                    <div className="space-y-2">
                        <h4 className="text-sm font-medium text-text-pri flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 text-danger" />
                            Red flags
                        </h4>
                        <div className="space-y-2">
                            {red_flags.map((f, i) => (
                                <div
                                    key={i}
                                    className="rounded-md border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-text-pri"
                                >
                                    {f}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {open_questions.length > 0 && (
                    <div className="space-y-2">
                        <h4 className="text-sm font-medium text-text-pri flex items-center gap-2">
                            <HelpCircle className="h-4 w-4 text-text-sec" />
                            Open questions
                        </h4>
                        <ul className="list-disc list-inside text-sm text-text-sec space-y-1">
                            {open_questions.slice(0, 10).map((q, i) => (
                                <li key={i}>{q}</li>
                            ))}
                            {open_questions.length > 10 && (
                                <li className="text-text-ter">+{open_questions.length - 10} more</li>
                            )}
                        </ul>
                    </div>
                )}

                {Object.keys(moat_evidence_by_pillar).length > 0 && (
                    <div className="space-y-2">
                        <h4 className="text-sm font-medium text-text-pri flex items-center gap-2">
                            <Shield className="h-4 w-4 text-text-sec" />
                            Moat evidence direction by pillar
                        </h4>
                        <div className="flex flex-wrap gap-2">
                            {Object.entries(moat_evidence_by_pillar).map(([pillar, directions]) => {
                                const counts = {};
                                for (const d of directions) {
                                    counts[d] = (counts[d] || 0) + 1;
                                }
                                const label = Object.entries(counts)
                                    .map(([k, v]) => `${k}: ${v}`)
                                    .join(', ');
                                return (
                                    <div
                                        key={pillar}
                                        className="rounded-md border border-border-subtle bg-surface-alt px-3 py-1.5 text-sm"
                                    >
                                        <span className="font-medium text-text-pri">{pillar}</span>
                                        <span className="text-text-sec ml-2">{label}</span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {tier_signals.length > 0 && (
                    <div className="space-y-2">
                        <h4 className="text-sm font-medium text-text-pri flex items-center gap-2">
                            <TrendingUp className="h-4 w-4 text-text-sec" />
                            Tier signals
                        </h4>
                        <div className="space-y-2">
                            {tier_signals.map((s, i) => (
                                <div
                                    key={i}
                                    className="rounded-md border border-border-subtle bg-surface-alt px-3 py-2 text-sm"
                                >
                                    <span className="font-medium text-text-pri">{s.direction}</span>
                                    {s.rationale && (
                                        <p className="text-text-sec mt-1">{s.rationale}</p>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
