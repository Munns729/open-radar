import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Check, X, ChevronRight } from 'lucide-react';

function formatAge(createdAt) {
    if (!createdAt) return '—';
    const date = new Date(createdAt);
    const now = new Date();
    const diffMs = now - date;
    const diffM = Math.floor(diffMs / 60000);
    const diffH = Math.floor(diffMs / 3600000);
    const diffD = Math.floor(diffMs / 86400000);
    if (diffM < 60) return `${diffM}m ago`;
    if (diffH < 24) return `${diffH}h ago`;
    return `${diffD}d ago`;
}

export default function ProposalQueue() {
    const navigate = useNavigate();
    const [proposals, setProposals] = useState([]);
    const [loading, setLoading] = useState(true);
    const [actingId, setActingId] = useState(null);
    const [noteById, setNoteById] = useState({});

    const fetchProposals = async () => {
        setLoading(true);
        try {
            const data = await api.getCanonProposals();
            setProposals(Array.isArray(data) ? data : []);
        } catch (e) {
            setProposals([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchProposals();
    }, []);

    const handleApprove = async (proposalId) => {
        setActingId(proposalId);
        try {
            await api.approveCanonProposal(proposalId, { reviewer_note: noteById[proposalId] || null });
            setNoteById((prev) => {
                const next = { ...prev };
                delete next[proposalId];
                return next;
            });
            await fetchProposals();
        } catch (e) {
            console.error('Approve failed:', e);
        } finally {
            setActingId(null);
        }
    };

    const handleReject = async (proposalId) => {
        setActingId(proposalId);
        try {
            await api.rejectCanonProposal(proposalId, { reviewer_note: noteById[proposalId] || null });
            setNoteById((prev) => {
                const next = { ...prev };
                delete next[proposalId];
                return next;
            });
            await fetchProposals();
        } catch (e) {
            console.error('Reject failed:', e);
        } finally {
            setActingId(null);
        }
    };

    const setNote = (proposalId, value) => {
        setNoteById((prev) => ({ ...prev, [proposalId]: value }));
    };

    const groupedByCompany = proposals.reduce((acc, p) => {
        const cid = p.company_id;
        if (!acc[cid]) acc[cid] = [];
        acc[cid].push(p);
        return acc;
    }, {});

    return (
        <Card className="border-border-subtle bg-surface">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-lg">Tier change proposals</CardTitle>
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
                                <TableHead className="text-text-ter">Company</TableHead>
                                <TableHead className="text-text-ter">Field</TableHead>
                                <TableHead className="text-text-ter">Current → Proposed</TableHead>
                                <TableHead className="text-text-ter">Rationale</TableHead>
                                <TableHead className="text-text-ter">Source</TableHead>
                                <TableHead className="text-text-ter">Age</TableHead>
                                <TableHead className="text-text-ter">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={7} className="text-center py-8 text-text-sec text-sm">
                                        Loading…
                                    </TableCell>
                                </TableRow>
                            ) : proposals.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={7} className="text-center py-8 text-text-sec text-sm">
                                        No pending proposals
                                    </TableCell>
                                </TableRow>
                            ) : (
                                Object.entries(groupedByCompany).flatMap(([companyId, list]) =>
                                    list.map((p) => (
                                        <TableRow
                                            key={p.id}
                                            className="hover:bg-surface-hover transition-colors"
                                        >
                                            <TableCell className="font-mono text-sm">
                                                <button
                                                    type="button"
                                                    onClick={() => navigate(`/tracker?company=${companyId}`)}
                                                    className="text-primary hover:text-primary-light"
                                                >
                                                    {companyId}
                                                </button>
                                            </TableCell>
                                            <TableCell className="text-sm">{p.proposed_field}</TableCell>
                                            <TableCell className="text-sm">
                                                <span className="text-text-sec line-through">{p.current_value || '—'}</span>
                                                <span className="mx-1 text-text-ter">→</span>
                                                <span className="font-medium text-text-pri">{p.proposed_value}</span>
                                            </TableCell>
                                            <TableCell className="text-sm text-text-sec max-w-[180px] truncate" title={p.rationale || ''}>
                                                {p.rationale || '—'}
                                            </TableCell>
                                            <TableCell>
                                                <Badge variant="outline" className="text-text-sec border-border-subtle text-xs">
                                                    {p.source_module || '—'}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-xs text-text-ter whitespace-nowrap">
                                                {formatAge(p.created_at)}
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex flex-col gap-1">
                                                    <Input
                                                        placeholder="Note (optional)"
                                                        className="h-8 text-xs"
                                                        value={noteById[p.id] ?? ''}
                                                        onChange={(e) => setNote(p.id, e.target.value)}
                                                    />
                                                    <div className="flex gap-1">
                                                        <Button
                                                            size="sm"
                                                            variant="default"
                                                            className="h-8 text-xs"
                                                            disabled={actingId !== null}
                                                            onClick={() => handleApprove(p.id)}
                                                        >
                                                            <Check className="h-3 w-3 mr-1" /> Approve
                                                        </Button>
                                                        <Button
                                                            size="sm"
                                                            variant="destructive"
                                                            className="h-8 text-xs"
                                                            disabled={actingId !== null}
                                                            onClick={() => handleReject(p.id)}
                                                        >
                                                            <X className="h-3 w-3 mr-1" /> Reject
                                                        </Button>
                                                    </div>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )
                            )}
                        </TableBody>
                    </Table>
                </div>
            </CardContent>
        </Card>
    );
}
