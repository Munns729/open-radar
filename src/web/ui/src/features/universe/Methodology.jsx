import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import {
    Info, ChevronDown, ChevronUp,
    Shield, Lock, Network, Globe, Award, Coins, Zap, Layers, Database, Star,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * Scoring Methodology panel.
 *
 * Pillar definitions are fetched from the /config/thesis API endpoint
 * so this component reflects whatever thesis is loaded, not hardcoded pillars.
 */

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

export default function Methodology() {
    const [isOpen, setIsOpen] = useState(false);
    const [pillars, setPillars] = useState([]);
    const [thesisName, setThesisName] = useState('');

    useEffect(() => {
        fetch('/config/thesis')
            .then((res) => res.json())
            .then((data) => {
                setThesisName(data.name || 'Investment Thesis');
                const pillarList = Object.entries(data.pillars || {}).map(
                    ([key, p]) => ({
                        key,
                        icon: ICON_MAP[key] || Shield,
                        title: p.name,
                        description: p.description,
                        weight: p.weight,
                    })
                );
                // Sort by weight descending
                pillarList.sort((a, b) => b.weight - a.weight);
                setPillars(pillarList);
            })
            .catch(() => {
                // Fallback: empty state, panel just won't show pillars
                setPillars([]);
            });
    }, []);

    return (
        <Card className="border-border/50 bg-surface-alt/50 backdrop-blur-xl mb-6">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors rounded-t-lg"
            >
                <div className="flex items-center gap-2">
                    <Info className="h-5 w-5 text-accent-main" />
                    <span className="font-semibold text-lg text-text-pri">Scoring Methodology</span>
                    {thesisName && (
                        <span className="text-xs text-text-sec ml-2">({thesisName})</span>
                    )}
                </div>
                {isOpen ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
            </button>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                    >
                        <CardContent className={`pt-0 pb-6 grid grid-cols-1 md:grid-cols-${Math.min(pillars.length, 5)} gap-4`}>
                            {pillars.map((p) => (
                                <div key={p.key} className="bg-background/40 p-3 rounded-lg border border-border/30">
                                    <div className="flex items-center gap-2 mb-2">
                                        <p.icon className="h-4 w-4 text-indigo-400" />
                                        <h4 className="font-medium text-sm text-indigo-200">{p.title}</h4>
                                        <span className="text-[10px] text-text-sec ml-auto">
                                            {(p.weight * 100).toFixed(0)}%
                                        </span>
                                    </div>
                                    <p className="text-xs text-muted-foreground leading-relaxed">
                                        {p.description}
                                    </p>
                                </div>
                            ))}
                            {pillars.length === 0 && (
                                <p className="text-xs text-text-sec col-span-full">
                                    No thesis configuration loaded.
                                </p>
                            )}
                        </CardContent>
                    </motion.div>
                )}
            </AnimatePresence>
        </Card>
    );
}
