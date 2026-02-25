import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Edit2, Save, X, RefreshCw } from 'lucide-react';

export default function CompanyCanonPanel({ companyId }) {
    const [canon, setCanon] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [editMode, setEditMode] = useState(false);
    const [editSummary, setEditSummary] = useState('');
    const [saving, setSaving] = useState(false);

    const fetchCanon = async () => {
        if (!companyId) return;
        setLoading(true);
        setError(null);
        try {
            const data = await api.getCanon(companyId);
            setCanon(data);
            setEditSummary(data.thesis_summary ?? '');
        } catch (e) {
            if (e.status === 404) {
                setCanon(null);
                setError('No canon record yet for this company.');
            } else {
                setError(e.message || 'Failed to load canon.');
            }
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchCanon();
    }, [companyId]);

    const handleSave = async () => {
        if (!companyId) return;
        setSaving(true);
        try {
            const data = await api.updateCanon(companyId, { thesis_summary: editSummary });
            setCanon(data);
            setEditMode(false);
        } catch (e) {
            console.error('Failed to update canon', e);
        } finally {
            setSaving(false);
        }
    };

    const handleCancel = () => {
        setEditSummary(canon?.thesis_summary ?? '');
        setEditMode(false);
    };

    if (loading) {
        return (
            <Card className="border-border-subtle bg-surface">
                <CardContent className="py-6 text-center text-text-sec text-sm">Loading canon...</CardContent>
            </Card>
        );
    }

    if (error && !canon) {
        return (
            <Card className="border-border-subtle bg-surface">
                <CardContent className="py-6 text-center text-text-sec text-sm">{error}</CardContent>
            </Card>
        );
    }

    const moatScores = canon?.current_moat_scores ?? canon?.moat_assessment ?? {};
    const pillarEntries = Object.entries(moatScores).filter(([k]) => k !== 'current_moat_scores');

    return (
        <Card className="border-border-subtle bg-surface">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-lg">Canon</CardTitle>
                {!editMode ? (
                    <Button variant="outline" size="sm" onClick={() => setEditMode(true)}>
                        <Edit2 className="h-4 w-4 mr-1" />
                        Edit
                    </Button>
                ) : (
                    <div className="flex gap-2">
                        <Button variant="ghost" size="sm" onClick={handleCancel} disabled={saving}>
                            <X className="h-4 w-4 mr-1" />
                            Cancel
                        </Button>
                        <Button size="sm" onClick={handleSave} disabled={saving}>
                            <Save className="h-4 w-4 mr-1" />
                            {saving ? 'Saving…' : 'Save'}
                        </Button>
                    </div>
                )}
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="flex flex-wrap gap-2">
                    {canon?.current_tier && (
                        <Badge className="bg-primary/10 text-primary border-primary/20">{canon.current_tier}</Badge>
                    )}
                    {canon?.coverage_status && (
                        <Badge variant="secondary">{canon.coverage_status}</Badge>
                    )}
                </div>

                <div>
                    <h3 className="text-sm font-medium text-text-sec mb-1">Thesis summary</h3>
                    {editMode ? (
                        <textarea
                            className="w-full min-h-[100px] p-3 bg-surface border border-border-subtle rounded-md text-sm text-text-pri focus:outline-none focus:ring-1 focus:ring-primary"
                            value={editSummary}
                            onChange={(e) => setEditSummary(e.target.value)}
                            placeholder="Investment thesis summary…"
                        />
                    ) : (
                        <p className="text-sm text-text-pri whitespace-pre-wrap">
                            {canon?.thesis_summary || '—'}
                        </p>
                    )}
                </div>

                {pillarEntries.length > 0 && (
                    <div>
                        <h3 className="text-sm font-medium text-text-sec mb-2">Moat scores</h3>
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                            {pillarEntries.map(([pillar, score]) => (
                                <div
                                    key={pillar}
                                    className="flex justify-between items-center p-2 rounded-lg bg-surface-alt border border-border-subtle"
                                >
                                    <span className="text-xs text-text-sec truncate">{pillar}</span>
                                    <span className="font-semibold text-text-pri">{score}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {canon?.open_questions?.length > 0 && (
                    <div>
                        <h3 className="text-sm font-medium text-text-sec mb-1">Open questions</h3>
                        <ul className="list-disc list-inside text-sm text-text-pri space-y-1">
                            {canon.open_questions.map((q, i) => (
                                <li key={i}>{q}</li>
                            ))}
                        </ul>
                    </div>
                )}

                {canon?.last_refreshed_at && (
                    <p className="text-xs text-text-ter flex items-center gap-1">
                        <RefreshCw className="h-3 w-3" />
                        Last refreshed {new Date(canon.last_refreshed_at).toLocaleString()}
                    </p>
                )}
            </CardContent>
        </Card>
    );
}
