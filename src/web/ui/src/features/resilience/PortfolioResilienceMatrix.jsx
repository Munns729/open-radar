import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';

const VERDICT_STYLES = {
    resilient: { bg: 'bg-emerald-500/15', text: 'text-emerald-400' },
    watch: { bg: 'bg-amber-500/15', text: 'text-amber-400' },
    exposed: { bg: 'bg-red-500/15', text: 'text-red-400' },
};

function VerdictBadge({ verdict }) {
    const style = VERDICT_STYLES[verdict] || { bg: 'bg-slate-500/15', text: 'text-slate-400' };
    return (
        <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${style.bg} ${style.text}`}>
            {verdict || '—'}
        </span>
    );
}

export default function PortfolioResilienceMatrix() {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [sortKey, setSortKey] = useState('l2_composite');
    const [sortDir, setSortDir] = useState('desc');

    useEffect(() => {
        api.getResiliencePortfolioMatrix()
            .then((res) => setData(Array.isArray(res) ? res : []))
            .catch(() => setData([]))
            .finally(() => setLoading(false));
    }, []);

    const sorted = [...data].sort((a, b) => {
        const va = a[sortKey];
        const vb = b[sortKey];
        if (va == null && vb == null) return 0;
        if (va == null) return sortDir === 'desc' ? 1 : -1;
        if (vb == null) return sortDir === 'desc' ? -1 : 1;
        if (typeof va === 'number' && typeof vb === 'number') {
            return sortDir === 'desc' ? vb - va : va - vb;
        }
        const s = String(va).localeCompare(String(vb));
        return sortDir === 'desc' ? -s : s;
    });

    const toggleSort = (key) => {
        if (sortKey === key) setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
        else setSortKey(key);
    };

    if (loading) {
        return (
            <div className="p-6 text-center text-text-sec text-sm">
                Loading portfolio matrix...
            </div>
        );
    }

    return (
        <Card className="border-border-subtle">
            <CardHeader>
                <CardTitle className="text-sm">Portfolio AI Resilience Matrix</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b border-border-subtle text-left text-text-sec">
                            <th
                                className="py-2 pr-4 cursor-pointer hover:text-text-pri"
                                onClick={() => toggleSort('company_name')}
                            >
                                Company
                            </th>
                            <th
                                className="py-2 pr-4 cursor-pointer hover:text-text-pri"
                                onClick={() => toggleSort('moat_score')}
                            >
                                Moat
                            </th>
                            <th className="py-2 pr-2">L1</th>
                            <th className="py-2 pr-2">L2</th>
                            <th className="py-2 pr-2">L3</th>
                            <th className="py-2 pr-2">L4</th>
                            <th
                                className="py-2 pl-2 cursor-pointer hover:text-text-pri"
                                onClick={() => toggleSort('l2_composite')}
                            >
                                L2 composite
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {sorted.map((row) => (
                            <tr key={row.company_id} className="border-b border-border-subtle/50 hover:bg-surface-hover/50">
                                <td className="py-2 pr-4 font-medium text-text-pri">{row.company_name}</td>
                                <td className="py-2 pr-4 text-text-sec">{row.moat_score ?? '—'}</td>
                                <td className="py-2 pr-2"><VerdictBadge verdict={row.l1_verdict} /></td>
                                <td className="py-2 pr-2"><VerdictBadge verdict={row.l2_verdict} /></td>
                                <td className="py-2 pr-2"><VerdictBadge verdict={row.l3_verdict} /></td>
                                <td className="py-2 pr-2"><VerdictBadge verdict={row.l4_verdict} /></td>
                                <td className="py-2 pl-2 font-mono text-text-pri">
                                    {row.l2_composite != null ? row.l2_composite.toFixed(1) : '—'}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                {sorted.length === 0 && (
                    <p className="py-8 text-center text-text-ter text-sm">No assessments yet.</p>
                )}
            </CardContent>
        </Card>
    );
}
