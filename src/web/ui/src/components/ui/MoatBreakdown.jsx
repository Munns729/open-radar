import React from 'react';
import {
    Shield,
    Lock,
    Network,
    Globe,
    Award,
    Coins,
    Zap,
    Layers,
    Database,
    Star,
} from 'lucide-react';

/**
 * Renders moat pillar scores from company.moat_attributes.
 *
 * Pillar keys are thesis-driven — this component reads whatever keys
 * are present in the data rather than hardcoding pillar names.
 * The reserved keys 'deal_screening' and 'risk_penalty' are excluded.
 */

// Icon lookup — provides sensible defaults for common pillar names.
// Unknown pillar keys get a generic Shield icon.
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
    retention: Star,
    integration: Layers,
    ecosystem: Network,
};

const COLOR_CYCLE = [
    'text-blue-400',
    'text-purple-400',
    'text-cyan-400',
    'text-amber-400',
    'text-emerald-400',
    'text-rose-400',
    'text-indigo-400',
    'text-teal-400',
];

const RESERVED_KEYS = new Set(['deal_screening', 'risk_penalty']);

function humanize(key) {
    return key
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

export const MoatBreakdown = ({ attributes }) => {
    if (!attributes) return null;

    // Derive pillar keys from the data itself — thesis-driven, not hardcoded
    const pillarKeys = Object.keys(attributes).filter(
        (k) => !RESERVED_KEYS.has(k)
    );

    return (
        <div className="flex gap-2 flex-wrap">
            {pillarKeys.map((key, idx) => {
                const data = attributes[key];
                if (!data || !data.present || data.score === 0) return null;
                const Icon = ICON_MAP[key] || Shield;
                const color = COLOR_CYCLE[idx % COLOR_CYCLE.length];
                const label = humanize(key);
                return (
                    <div
                        key={key}
                        className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-alt border border-border-subtle group relative cursor-help"
                        title={`${label}: ${data.score}% - ${data.justification}`}
                    >
                        <Icon className={`h-3 w-3 ${color}`} />
                        <span className="text-[10px] font-bold text-text-pri">{data.score}</span>

                        {/* Tooltip on hover */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-48 p-2 bg-surface-alt border border-border-subtle rounded shadow-xl z-50 pointer-events-none">
                            <p className="text-[10px] font-bold text-text-pri mb-1">{label}</p>
                            <p className="text-[9px] text-text-sec leading-tight">{data.justification}</p>
                        </div>
                    </div>
                );
            })}
        </div>
    );
};
