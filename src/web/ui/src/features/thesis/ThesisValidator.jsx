import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
    ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
} from 'recharts';
import {
    FlaskConical, Search, Shield, Lock, Network, Globe, Award, Coins,
    Zap, Layers, Database, Star, TrendingUp, AlertTriangle, CheckCircle2,
    XCircle, ChevronRight, ExternalLink, Trophy, BarChart3, Info,
    ArrowUpRight, ArrowDownRight, Minus, Building2,
} from 'lucide-react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { useCurrency } from '@/context/CurrencyContext';

// --- Icon map (matches MoatBreakdown.jsx convention) ---
const ICON_MAP = {
    regulatory: Lock,
    network: Network,
    geographic: Globe,
    liability: Award,
    physical: Coins,
    switching_costs: Layers,
    ip: Zap,
    data_moat: Database,
    brand: Star,
};

const PILLAR_COLORS = {
    regulatory: '#818cf8',
    network: '#a78bfa',
    geographic: '#22d3ee',
    liability: '#fbbf24',
    physical: '#34d399',
};

const TIER_COLORS = {
    TIER_1A: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/30', label: 'Tier 1A' },
    TIER_1B: { bg: 'bg-blue-500/15', text: 'text-blue-400', border: 'border-blue-500/30', label: 'Tier 1B' },
    TIER_2: { bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30', label: 'Tier 2' },
    WAITLIST: { bg: 'bg-slate-500/15', text: 'text-slate-400', border: 'border-slate-500/30', label: 'Waitlist' },
};

function humanize(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

// ─── Tier Badge ─────────────────────────────────────────────
function TierBadge({ tier }) {
    const cfg = TIER_COLORS[tier] || TIER_COLORS.WAITLIST;
    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${cfg.bg} ${cfg.text} ${cfg.border}`}>
            {cfg.label}
        </span>
    );
}

// ─── Score Gauge ────────────────────────────────────────────
function ScoreGauge({ score, thresholds }) {
    const pct = Math.min(score, 100);
    let color = '#64748b';
    if (score >= thresholds.tier_1a) color = '#10b981';
    else if (score >= thresholds.tier_1b) color = '#3b82f6';
    else if (score >= thresholds.tier_2) color = '#f59e0b';

    return (
        <div className="relative w-32 h-32 mx-auto">
            <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                <circle cx="50" cy="50" r="42" fill="none" stroke="currentColor"
                    className="text-border-subtle" strokeWidth="6" />
                <circle cx="50" cy="50" r="42" fill="none" stroke={color}
                    strokeWidth="6" strokeLinecap="round"
                    strokeDasharray={`${pct * 2.64} ${264 - pct * 2.64}`} />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-text-pri">{score}</span>
                <span className="text-[10px] text-text-sec">/ 100</span>
            </div>
        </div>
    );
}

// ─── Threshold Bar ──────────────────────────────────────────
function ThresholdBar({ score, thresholds }) {
    const marks = [
        { val: thresholds.tier_2, label: 'T2', color: '#f59e0b' },
        { val: thresholds.tier_1b, label: '1B', color: '#3b82f6' },
        { val: thresholds.tier_1a, label: '1A', color: '#10b981' },
    ];
    return (
        <div className="mt-3">
            <div className="relative h-2 bg-surface-alt rounded-full overflow-hidden">
                <motion.div
                    className="absolute left-0 top-0 h-full rounded-full"
                    style={{ backgroundColor: score >= thresholds.tier_1a ? '#10b981' : score >= thresholds.tier_1b ? '#3b82f6' : score >= thresholds.tier_2 ? '#f59e0b' : '#64748b' }}
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(score, 100)}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                />
            </div>
            <div className="relative h-4 mt-0.5">
                {marks.map(m => (
                    <div key={m.label} className="absolute -translate-x-1/2 flex flex-col items-center"
                        style={{ left: `${m.val}%` }}>
                        <div className="w-px h-2" style={{ backgroundColor: m.color }} />
                        <span className="text-[9px] font-medium" style={{ color: m.color }}>{m.label}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ─── Pillar Card ────────────────────────────────────────────
function PillarCard({ pillar }) {
    const Icon = ICON_MAP[pillar.key] || Shield;
    const color = PILLAR_COLORS[pillar.key] || '#94a3b8';
    const meetsThreshold = pillar.raw_score >= pillar.evidence_threshold;

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-surface border border-border-subtle rounded-xl p-4 hover:border-primary/30 transition-colors"
        >
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-lg" style={{ backgroundColor: `${color}20` }}>
                        <Icon className="h-4 w-4" style={{ color }} />
                    </div>
                    <div>
                        <h4 className="text-sm font-semibold text-text-pri">{pillar.name}</h4>
                        <span className="text-[10px] text-text-ter">
                            Weight: {(pillar.weight * 100).toFixed(0)}% · Threshold: {pillar.evidence_threshold}
                        </span>
                    </div>
                </div>
                <div className="text-right">
                    <span className="text-xl font-bold" style={{ color: meetsThreshold ? color : '#64748b' }}>
                        {pillar.raw_score}
                    </span>
                    <span className="text-xs text-text-ter">/{pillar.max_raw_score}</span>
                </div>
            </div>

            {/* Score bar */}
            <div className="h-1.5 bg-surface-alt rounded-full mb-2 overflow-hidden">
                <motion.div
                    className="h-full rounded-full"
                    style={{ backgroundColor: meetsThreshold ? color : '#475569' }}
                    initial={{ width: 0 }}
                    animate={{ width: `${(pillar.raw_score / pillar.max_raw_score) * 100}%` }}
                    transition={{ duration: 0.6, delay: 0.1 }}
                />
            </div>

            <div className="flex items-center gap-1.5 mb-2">
                {meetsThreshold ? (
                    <CheckCircle2 className="h-3 w-3 text-emerald-400 flex-shrink-0" />
                ) : (
                    <XCircle className="h-3 w-3 text-slate-500 flex-shrink-0" />
                )}
                <span className={`text-[11px] font-medium ${meetsThreshold ? 'text-emerald-400' : 'text-text-ter'}`}>
                    {meetsThreshold ? 'Evidence threshold met' : 'Below evidence threshold'}
                </span>
            </div>

            {pillar.justification && (
                <p className="text-xs text-text-sec leading-relaxed line-clamp-3">
                    {pillar.justification}
                </p>
            )}

            {meetsThreshold && (
                <div className="mt-2 pt-2 border-t border-border-subtle">
                    <div className="flex justify-between text-[10px]">
                        <span className="text-text-ter">Weighted contribution</span>
                        <span className="font-semibold text-text-pri">
                            +{pillar.weighted_contribution?.toFixed?.(1) ?? pillar.weighted_contribution}
                        </span>
                    </div>
                </div>
            )}
        </motion.div>
    );
}

// ─── Company Search ─────────────────────────────────────────
function CompanySearch({ onSelect }) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [searching, setSearching] = useState(false);

    const search = useCallback(async (q) => {
        if (q.length < 2) { setResults([]); return; }
        setSearching(true);
        try {
            const data = await api.getCompanies({ search: q, limit: 8, is_scored: true });
            setResults(data?.data || data || []);
        } catch { setResults([]); }
        setSearching(false);
    }, []);

    useEffect(() => {
        const timer = setTimeout(() => search(query), 300);
        return () => clearTimeout(timer);
    }, [query, search]);

    return (
        <div className="relative">
            <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-ter" />
                <input
                    type="text"
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    placeholder="Search scored companies..."
                    className="w-full pl-10 pr-4 py-2.5 bg-surface border border-border-subtle rounded-lg text-sm text-text-pri placeholder:text-text-ter focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
                />
                {searching && (
                    <div className="absolute right-3 top-1/2 -translate-y-1/2">
                        <div className="h-4 w-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                    </div>
                )}
            </div>
            <AnimatePresence>
                {results.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: -4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -4 }}
                        className="absolute z-50 w-full mt-1 bg-surface border border-border-subtle rounded-lg shadow-2xl overflow-hidden max-h-64 overflow-y-auto"
                    >
                        {results.map(c => (
                            <button
                                key={c.id}
                                onClick={() => { onSelect(c.id); setQuery(''); setResults([]); }}
                                className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-surface-hover transition-colors text-left"
                            >
                                <div>
                                    <span className="text-sm font-medium text-text-pri">{c.name}</span>
                                    <div className="flex items-center gap-2 mt-0.5">
                                        <span className="text-[10px] text-text-ter">{c.sector || 'Unknown'}</span>
                                        <span className="text-[10px] text-text-ter">·</span>
                                        <span className="text-[10px] text-text-ter">{c.hq_country || '—'}</span>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-sm font-bold text-text-pri">{c.moat_score}</span>
                                    {c.tier && <TierBadge tier={c.tier} />}
                                </div>
                            </button>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

// ─── Leaderboard Table ──────────────────────────────────────
function Leaderboard({ onSelect }) {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    const { convert, currency } = useCurrency();

    useEffect(() => {
        api.getThesisLeaderboard({ limit: 15 })
            .then(d => setData(d || []))
            .catch(() => setData([]))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return <div className="text-center py-8 text-text-ter text-sm">Loading leaderboard...</div>;

    return (
        <div className="space-y-1">
            {data.map((c, i) => (
                <button
                    key={c.id}
                    onClick={() => onSelect(c.id)}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-surface-hover transition-colors text-left"
                >
                    <span className={`w-6 text-center text-xs font-bold ${i < 3 ? 'text-amber-400' : 'text-text-ter'}`}>
                        {i + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-text-pri truncate">{c.name}</span>
                            {c.tier && <TierBadge tier={c.tier} />}
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-[10px] text-text-ter">{c.sector || '—'}</span>
                            {c.strongest_pillar && (
                                <>
                                    <span className="text-[10px] text-text-ter">·</span>
                                    <span className="text-[10px] font-medium" style={{ color: PILLAR_COLORS[c.strongest_pillar] || '#94a3b8' }}>
                                        {humanize(c.strongest_pillar)} ({c.strongest_pillar_score})
                                    </span>
                                </>
                            )}
                        </div>
                    </div>
                    <span className="text-lg font-bold text-text-pri">{c.moat_score}</span>
                    <ChevronRight className="h-4 w-4 text-text-ter" />
                </button>
            ))}
            {data.length === 0 && (
                <p className="text-center py-8 text-text-ter text-sm">No scored companies found.</p>
            )}
        </div>
    );
}

// ─── Pillar Distribution Chart ──────────────────────────────
function DistributionChart() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.getThesisDistribution()
            .then(d => setData(d))
            .catch(() => setData(null))
            .finally(() => setLoading(false));
    }, []);

    if (loading || !data) return null;

    const chartData = Object.entries(data.pillars || {}).map(([key, p]) => ({
        name: p.name.split(' ')[0], // Short label
        avg: p.avg_score,
        pct: p.present_pct,
        fill: PILLAR_COLORS[key] || '#94a3b8',
    }));

    return (
        <Card className="border-border-subtle">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-primary" />
                    Universe Distribution
                    <span className="text-[10px] text-text-ter font-normal ml-auto">
                        {data.total_scored} companies scored
                    </span>
                </CardTitle>
            </CardHeader>
            <CardContent>
                <ResponsiveContainer width="100%" height={160}>
                    <BarChart data={chartData} barSize={28}>
                        <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} domain={[0, 100]} />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
                            formatter={(val, name) => [name === 'avg' ? `${val} avg score` : `${val}% have evidence`, '']}
                        />
                        <Bar dataKey="avg" radius={[4, 4, 0, 0]}>
                            {chartData.map((entry, idx) => (
                                <Cell key={idx} fill={entry.fill} fillOpacity={0.7} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
                <div className="grid grid-cols-5 gap-1 mt-2">
                    {chartData.map(d => (
                        <div key={d.name} className="text-center">
                            <span className="text-[10px] font-semibold" style={{ color: d.fill }}>{d.pct}%</span>
                            <span className="text-[9px] text-text-ter block">have evidence</span>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}

// ═════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═════════════════════════════════════════════════════════════
export default function ThesisValidator() {
    const [thesisConfig, setThesisConfig] = useState(null);
    const [validation, setValidation] = useState(null);
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('validate'); // validate | leaderboard
    const { convert, currency } = useCurrency();

    const formatMoney = (amount) => {
        if (!amount) return '—';
        const converted = convert(amount);
        const symbol = currency === 'USD' ? '$' : currency === 'EUR' ? '€' : '£';
        return `${symbol}${(converted / 1_000_000).toFixed(1)}M`;
    };

    // Load thesis config on mount
    useEffect(() => {
        api.getThesisConfig()
            .then(d => setThesisConfig(d))
            .catch(() => setThesisConfig(null));
    }, []);

    const handleSelectCompany = async (companyId) => {
        setLoading(true);
        try {
            const data = await api.validateCompany(companyId);
            setValidation(data);
        } catch (err) {
            console.error('Validation failed:', err);
            setValidation(null);
        }
        setLoading(false);
    };

    // Radar chart data
    const radarData = validation?.pillar_breakdown?.map(p => ({
        pillar: p.name.split('&')[0].trim().split(' ')[0],
        score: p.raw_score,
        fullMark: p.max_raw_score,
    })) || [];

    const tabs = [
        { key: 'validate', label: 'Validate', icon: FlaskConical },
        { key: 'leaderboard', label: 'Leaderboard', icon: Trophy },
    ];

    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
        >
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-text-pri flex items-center gap-2">
                        <FlaskConical className="h-6 w-6 text-primary" />
                        Thesis Validator
                    </h1>
                    {thesisConfig && (
                        <p className="text-sm text-text-sec mt-1">
                            {thesisConfig.name} v{thesisConfig.version} · {Object.keys(thesisConfig.pillars || {}).length} pillars · {thesisConfig.certification_count} certifications tracked
                        </p>
                    )}
                </div>
                <div className="flex bg-surface border border-border-subtle rounded-lg p-0.5">
                    {tabs.map(t => (
                        <button
                            key={t.key}
                            onClick={() => setActiveTab(t.key)}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${activeTab === t.key ? 'bg-primary/10 text-primary' : 'text-text-sec hover:text-text-pri'}`}
                        >
                            <t.icon className="h-3.5 w-3.5" />
                            {t.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Thesis Overview Bar */}
            {thesisConfig && (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                    {Object.entries(thesisConfig.pillars || {}).map(([key, p]) => {
                        const Icon = ICON_MAP[key] || Shield;
                        const color = PILLAR_COLORS[key] || '#94a3b8';
                        return (
                            <div key={key} className="flex items-center gap-2 bg-surface border border-border-subtle rounded-lg px-3 py-2">
                                <Icon className="h-4 w-4 flex-shrink-0" style={{ color }} />
                                <div className="min-w-0">
                                    <span className="text-xs font-medium text-text-pri truncate block">{p.name}</span>
                                    <span className="text-[10px] text-text-ter">{(p.weight * 100).toFixed(0)}% weight</span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Tab Content */}
            <AnimatePresence mode="wait">
                {activeTab === 'validate' && (
                    <motion.div
                        key="validate"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="space-y-6"
                    >
                        {/* Search */}
                        <Card className="border-border-subtle">
                            <CardContent className="pt-4">
                                <CompanySearch onSelect={handleSelectCompany} />
                            </CardContent>
                        </Card>

                        {/* Loading state */}
                        {loading && (
                            <div className="flex items-center justify-center py-16">
                                <div className="flex flex-col items-center gap-3">
                                    <div className="h-8 w-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                                    <span className="text-sm text-text-sec">Validating against thesis...</span>
                                </div>
                            </div>
                        )}

                        {/* Empty state */}
                        {!loading && !validation && (
                            <div className="flex flex-col items-center justify-center py-16">
                                <div className="p-4 bg-primary/5 rounded-2xl mb-4">
                                    <FlaskConical className="h-10 w-10 text-primary/50" />
                                </div>
                                <h3 className="text-lg font-semibold text-text-pri mb-1">Select a Company</h3>
                                <p className="text-sm text-text-sec max-w-md text-center">
                                    Search for a scored company above to see how it performs against the active investment thesis, pillar by pillar.
                                </p>
                            </div>
                        )}

                        {/* Validation Results */}
                        {!loading && validation && (
                            <motion.div
                                initial={{ opacity: 0, y: 12 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="space-y-6"
                            >
                                {/* Company Header + Score */}
                                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                    {/* Company Info */}
                                    <Card className="border-border-subtle lg:col-span-2">
                                        <CardContent className="pt-4">
                                            <div className="flex items-start justify-between">
                                                <div>
                                                    <div className="flex items-center gap-3 mb-1">
                                                        <h2 className="text-xl font-bold text-text-pri">{validation.company.name}</h2>
                                                        <TierBadge tier={validation.company.tier} />
                                                    </div>
                                                    <div className="flex items-center gap-3 text-sm text-text-sec">
                                                        {validation.company.sector && <span>{validation.company.sector}</span>}
                                                        {validation.company.sub_sector && <span className="text-text-ter">/ {validation.company.sub_sector}</span>}
                                                        {validation.company.hq_country && (
                                                            <>
                                                                <span className="text-text-ter">·</span>
                                                                <span className="flex items-center gap-1">
                                                                    <Globe className="h-3 w-3" />
                                                                    {validation.company.hq_country}
                                                                    {validation.company.hq_city && `, ${validation.company.hq_city}`}
                                                                </span>
                                                            </>
                                                        )}
                                                    </div>
                                                    {validation.company.description && (
                                                        <p className="mt-3 text-xs text-text-sec leading-relaxed max-w-xl line-clamp-3">
                                                            {validation.company.description}
                                                        </p>
                                                    )}
                                                </div>
                                                {validation.company.website && (
                                                    <a href={validation.company.website.startsWith('http') ? validation.company.website : `https://${validation.company.website}`}
                                                        target="_blank" rel="noopener noreferrer"
                                                        className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 flex-shrink-0">
                                                        <ExternalLink className="h-3 w-3" /> Website
                                                    </a>
                                                )}
                                            </div>

                                            {/* Financials row */}
                                            <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-border-subtle">
                                                <div>
                                                    <span className="text-[10px] text-text-ter uppercase tracking-wider">Revenue</span>
                                                    <p className="text-sm font-semibold text-text-pri">{formatMoney(validation.company.revenue_gbp)}</p>
                                                    {validation.company.revenue_source && validation.company.revenue_source !== 'llm_website' && (
                                                        <p className="text-[10px] text-text-ter mt-0.5" title="Data provenance">
                                                            {validation.company.revenue_source === 'ch_band_midpoint' && 'CH account band midpoint'}
                                                            {validation.company.revenue_source === 'eu_band_midpoint' && 'EU SME band midpoint'}
                                                            {validation.company.revenue_source === 'ch_filing' && 'From filings'}
                                                        </p>
                                                    )}
                                                </div>
                                                <div>
                                                    <span className="text-[10px] text-text-ter uppercase tracking-wider">EBITDA</span>
                                                    <p className="text-sm font-semibold text-text-pri">{formatMoney(validation.company.ebitda_gbp)}</p>
                                                </div>
                                                <div>
                                                    <span className="text-[10px] text-text-ter uppercase tracking-wider">Margin</span>
                                                    <p className="text-sm font-semibold text-text-pri">
                                                        {validation.company.ebitda_margin != null ? `${validation.company.ebitda_margin}%` : '—'}
                                                    </p>
                                                </div>
                                                <div>
                                                    <span className="text-[10px] text-text-ter uppercase tracking-wider">Employees</span>
                                                    <p className="text-sm font-semibold text-text-pri">
                                                        {validation.company.employees?.toLocaleString() || '—'}
                                                    </p>
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>

                                    {/* Score + Radar */}
                                    <Card className="border-border-subtle">
                                        <CardContent className="pt-4 flex flex-col items-center">
                                            <ScoreGauge
                                                score={validation.company.moat_score}
                                                thresholds={validation.tier_thresholds}
                                            />
                                            <ThresholdBar
                                                score={validation.company.moat_score}
                                                thresholds={validation.tier_thresholds}
                                            />
                                            <p className="text-[10px] text-text-ter mt-2 text-center">
                                                {validation.thesis.name} v{validation.thesis.version}
                                            </p>

                                            {/* Risk penalty */}
                                            {validation.risk?.present && (
                                                <div className="mt-3 flex items-center gap-1.5 px-2 py-1 bg-red-500/10 border border-red-500/20 rounded-md">
                                                    <AlertTriangle className="h-3 w-3 text-red-400" />
                                                    <span className="text-[10px] text-red-400 font-medium">
                                                        {validation.risk.penalty} point penalty: {validation.risk.justification}
                                                    </span>
                                                </div>
                                            )}
                                        </CardContent>
                                    </Card>
                                </div>

                                {/* Radar Chart + Deal Screening */}
                                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                    {/* Radar Chart */}
                                    <Card className="border-border-subtle lg:col-span-2">
                                        <CardHeader className="pb-0">
                                            <CardTitle className="text-sm">Pillar Radar</CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <ResponsiveContainer width="100%" height={280}>
                                                <RadarChart data={radarData}>
                                                    <PolarGrid stroke="#334155" />
                                                    <PolarAngleAxis
                                                        dataKey="pillar"
                                                        tick={{ fontSize: 11, fill: '#94a3b8' }}
                                                    />
                                                    <PolarRadiusAxis
                                                        angle={90}
                                                        domain={[0, 100]}
                                                        tick={{ fontSize: 9, fill: '#64748b' }}
                                                    />
                                                    <Radar
                                                        dataKey="score"
                                                        stroke="#818cf8"
                                                        fill="#818cf8"
                                                        fillOpacity={0.2}
                                                        strokeWidth={2}
                                                    />
                                                </RadarChart>
                                            </ResponsiveContainer>
                                        </CardContent>
                                    </Card>

                                    {/* Deal Screening + Certs */}
                                    <div className="space-y-4">
                                        <Card className="border-border-subtle">
                                            <CardHeader className="pb-2">
                                                <CardTitle className="text-sm flex items-center gap-2">
                                                    <TrendingUp className="h-4 w-4 text-emerald-400" />
                                                    Deal Screening
                                                </CardTitle>
                                            </CardHeader>
                                            <CardContent className="space-y-3">
                                                <div>
                                                    <div className="flex justify-between text-xs mb-1">
                                                        <span className="text-text-sec">Financial Fit</span>
                                                        <span className="font-semibold text-text-pri">
                                                            {validation.deal_screening.financial_fit.score}
                                                        </span>
                                                    </div>
                                                    {validation.deal_screening.financial_fit.factors?.map((f, i) => (
                                                        <span key={i} className="inline-flex items-center gap-1 text-[10px] text-emerald-400 mr-2">
                                                            <CheckCircle2 className="h-2.5 w-2.5" /> {f}
                                                        </span>
                                                    ))}
                                                </div>
                                                <div>
                                                    <div className="flex justify-between text-xs mb-1">
                                                        <span className="text-text-sec">Competitive Position</span>
                                                        <span className="font-semibold text-text-pri">
                                                            {validation.deal_screening.competitive_position.score}
                                                        </span>
                                                    </div>
                                                    {validation.deal_screening.competitive_position.factors?.map((f, i) => (
                                                        <span key={i} className="inline-flex items-center gap-1 text-[10px] text-blue-400 mr-2">
                                                            <CheckCircle2 className="h-2.5 w-2.5" /> {f}
                                                        </span>
                                                    ))}
                                                </div>
                                                <div className="pt-2 border-t border-border-subtle flex justify-between">
                                                    <span className="text-xs font-medium text-text-sec">Total Deal Score</span>
                                                    <span className="text-sm font-bold text-text-pri">{validation.deal_screening.total_score}</span>
                                                </div>
                                            </CardContent>
                                        </Card>

                                        {/* Certifications */}
                                        {validation.certifications?.length > 0 && (
                                            <Card className="border-border-subtle">
                                                <CardHeader className="pb-2">
                                                    <CardTitle className="text-sm flex items-center gap-2">
                                                        <Shield className="h-4 w-4 text-amber-400" />
                                                        Certifications
                                                    </CardTitle>
                                                </CardHeader>
                                                <CardContent className="space-y-1.5">
                                                    {validation.certifications.map((c, i) => (
                                                        <div key={i} className="flex items-center justify-between text-xs">
                                                            <div className="flex items-center gap-2">
                                                                <Lock className="h-3 w-3 text-text-ter" />
                                                                <span className="text-text-pri font-medium">{c.type}</span>
                                                            </div>
                                                            <span className={`font-semibold ${c.thesis_score > 0 ? 'text-amber-400' : 'text-text-ter'}`}>
                                                                +{c.thesis_score}
                                                            </span>
                                                        </div>
                                                    ))}
                                                </CardContent>
                                            </Card>
                                        )}
                                    </div>
                                </div>

                                {/* Pillar Breakdown Cards */}
                                <div>
                                    <h3 className="text-sm font-semibold text-text-pri mb-3">Pillar Analysis</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                        {validation.pillar_breakdown.map(p => (
                                            <PillarCard key={p.key} pillar={p} />
                                        ))}
                                    </div>
                                </div>

                                {/* Analysis Reasoning */}
                                {validation.analysis_metadata?.reasoning && (
                                    <Card className="border-border-subtle">
                                        <CardContent className="pt-4">
                                            <div className="flex items-start gap-2">
                                                <Info className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                                                <div>
                                                    <h4 className="text-xs font-semibold text-text-pri mb-1">AI Analysis Summary</h4>
                                                    <p className="text-xs text-text-sec leading-relaxed">
                                                        {validation.analysis_metadata.reasoning}
                                                    </p>
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>
                                )}

                                {/* Scoring History */}
                                {validation.scoring_history?.length > 0 && (
                                    <Card className="border-border-subtle">
                                        <CardHeader className="pb-2">
                                            <CardTitle className="text-sm">Scoring History</CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <div className="space-y-2">
                                                {validation.scoring_history.map((evt, i) => (
                                                    <div key={evt.id || i} className="flex items-center gap-3 text-xs">
                                                        <span className="text-text-ter w-28 flex-shrink-0">
                                                            {evt.scored_at ? new Date(evt.scored_at).toLocaleDateString() : '—'}
                                                        </span>
                                                        <span className="font-bold text-text-pri w-8">{evt.moat_score}</span>
                                                        {evt.score_delta != null && evt.score_delta !== 0 && (
                                                            <span className={`flex items-center gap-0.5 ${evt.score_delta > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                                {evt.score_delta > 0 ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                                                                {evt.score_delta > 0 ? '+' : ''}{evt.score_delta}
                                                            </span>
                                                        )}
                                                        {evt.score_delta === 0 && <Minus className="h-3 w-3 text-text-ter" />}
                                                        <TierBadge tier={evt.tier} />
                                                        <span className="text-text-ter ml-auto">{evt.trigger}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </CardContent>
                                    </Card>
                                )}
                            </motion.div>
                        )}
                    </motion.div>
                )}

                {activeTab === 'leaderboard' && (
                    <motion.div
                        key="leaderboard"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="grid grid-cols-1 lg:grid-cols-3 gap-6"
                    >
                        <Card className="border-border-subtle lg:col-span-2">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm flex items-center gap-2">
                                    <Trophy className="h-4 w-4 text-amber-400" />
                                    Top Companies by Thesis Score
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <Leaderboard onSelect={(id) => { handleSelectCompany(id); setActiveTab('validate'); }} />
                            </CardContent>
                        </Card>

                        <div className="space-y-4">
                            <DistributionChart />

                            {/* Thesis Summary */}
                            {thesisConfig && (
                                <Card className="border-border-subtle">
                                    <CardHeader className="pb-2">
                                        <CardTitle className="text-sm flex items-center gap-2">
                                            <Info className="h-4 w-4 text-primary" />
                                            Thesis Summary
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent className="space-y-2">
                                        <p className="text-xs text-text-sec leading-relaxed">{thesisConfig.description}</p>
                                        <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border-subtle">
                                            <div>
                                                <span className="text-[10px] text-text-ter">Revenue Range</span>
                                                <p className="text-xs font-semibold text-text-pri">
                                                    {thesisConfig.business_filters?.min_revenue ? `£${(thesisConfig.business_filters.min_revenue / 1e6).toFixed(0)}M` : '—'}
                                                    {' – '}
                                                    {thesisConfig.business_filters?.max_revenue ? `£${(thesisConfig.business_filters.max_revenue / 1e6).toFixed(0)}M` : '—'}
                                                </p>
                                            </div>
                                            <div>
                                                <span className="text-[10px] text-text-ter">Employees</span>
                                                <p className="text-xs font-semibold text-text-pri">
                                                    {thesisConfig.business_filters?.min_employees || '—'}
                                                    {' – '}
                                                    {thesisConfig.business_filters?.max_employees || '—'}
                                                </p>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            )}
                        </div>
                    </motion.div>
                )}

            </AnimatePresence>
        </motion.div>
    );
}
