import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Zap, Loader2 } from 'lucide-react';

const VERDICT_STYLES = {
    resilient: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/30' },
    watch: { bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30' },
    exposed: { bg: 'bg-red-500/15', text: 'text-red-400', border: 'border-red-500/30' },
};

function VerdictBadge({ verdict }) {
    const style = VERDICT_STYLES[verdict] || { bg: 'bg-slate-500/15', text: 'text-slate-400', border: 'border-slate-500/30' };
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${style.bg} ${style.text} ${style.border}`}>
            {verdict || '—'}
        </span>
    );
}

function MiniBar({ label, value, max = 5 }) {
    const pct = value != null ? (value / max) * 100 : 0;
    return (
        <div className="flex items-center gap-2">
            <span className="text-[10px] text-text-sec w-20 truncate">{label}</span>
            <div className="flex-1 h-1.5 bg-surface-alt rounded-full overflow-hidden">
                <div
                    className="h-full rounded-full bg-primary/70"
                    style={{ width: `${pct}%` }}
                />
            </div>
            <span className="text-[10px] font-mono w-4 text-right">{value ?? '—'}</span>
        </div>
    );
}

function LevelColumn({ level, assessment, companyId, onAssessAutomated, assessing }) {
    const a = assessment;
    const verdict = a?.overall_verdict;
    const composite = a?.composite_score;

    return (
        <Card className="border-border-subtle flex-1 min-w-0">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center justify-between">
                    <span>L{level}</span>
                    <VerdictBadge verdict={verdict} />
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
                {composite != null && (
                    <p className="text-lg font-bold text-text-pri">{composite.toFixed(1)}</p>
                )}
                {a && (
                    <>
                        <MiniBar label="Substitution" value={a.substitution_score} />
                        <MiniBar label="Disintermediation" value={a.disintermediation_score} />
                        <MiniBar label="Amplification" value={a.amplification_score} />
                        <MiniBar label="Cost disruption" value={a.cost_disruption_score} />
                        {a.assessed_at && (
                            <p className="text-[10px] text-text-ter pt-1">
                                {new Date(a.assessed_at).toLocaleString()}
                            </p>
                        )}
                    </>
                )}
                {!a && (
                    <p className="text-xs text-text-ter">No assessment yet</p>
                )}
                <Button
                    size="sm"
                    variant="outline"
                    className="w-full mt-2"
                    disabled={assessing}
                    onClick={() => onAssessAutomated(level)}
                >
                    {assessing ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />
                    ) : (
                        <Zap className="h-3.5 w-3.5 mr-1" />
                    )}
                    Automated Assess
                </Button>
            </CardContent>
        </Card>
    );
}

export default function CompanyResiliencePanel({ companyId }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [assessingLevel, setAssessingLevel] = useState(null);

    const fetchAssessments = async () => {
        if (!companyId) return;
        setLoading(true);
        try {
            const res = await api.getResilienceAssessments(companyId);
            setData(res?.levels ? { company_id: companyId, levels: res.levels } : res);
        } catch (e) {
            console.error('Failed to fetch resilience assessments', e);
            setData(null);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAssessments();
    }, [companyId]);

    const handleAssessAutomated = async (level) => {
        setAssessingLevel(level);
        try {
            await api.postResilienceAssessAutomated(companyId, { capability_level: level });
            setTimeout(() => fetchAssessments(), 2000);
        } catch (e) {
            console.error('Automated assess failed', e);
        } finally {
            setAssessingLevel(null);
        }
    };

    if (loading && !data) {
        return (
            <div className="p-6 text-center text-text-sec text-sm">
                Loading resilience assessments...
            </div>
        );
    }

    const levels = data?.levels || {};

    return (
        <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <LevelColumn
                    level={1}
                    assessment={levels['1']}
                    companyId={companyId}
                    onAssessAutomated={handleAssessAutomated}
                    assessing={assessingLevel === 1}
                />
                <LevelColumn
                    level={2}
                    assessment={levels['2']}
                    companyId={companyId}
                    onAssessAutomated={handleAssessAutomated}
                    assessing={assessingLevel === 2}
                />
                <LevelColumn
                    level={3}
                    assessment={levels['3']}
                    companyId={companyId}
                    onAssessAutomated={handleAssessAutomated}
                    assessing={assessingLevel === 3}
                />
                <LevelColumn
                    level={4}
                    assessment={levels['4']}
                    companyId={companyId}
                    onAssessAutomated={handleAssessAutomated}
                    assessing={assessingLevel === 4}
                />
            </div>
        </div>
    );
}
