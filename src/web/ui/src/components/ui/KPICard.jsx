import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

export function KPICard({
    title,
    value,
    icon: Icon,
    change,
    changeType = 'neutral', // 'positive', 'negative', 'neutral'
    loading = false,
    className
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
                "p-5 bg-surface border border-border-subtle rounded-xl hover:border-border transition-colors",
                className
            )}
        >
            {loading ? (
                <div className="animate-pulse">
                    <div className="h-4 w-24 bg-surface-alt rounded mb-3" />
                    <div className="h-8 w-16 bg-surface-alt rounded" />
                </div>
            ) : (
                <>
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-sm font-medium text-text-sec">{title}</span>
                        {Icon && (
                            <div className="p-2 bg-primary/10 rounded-lg">
                                <Icon className="h-4 w-4 text-primary" />
                            </div>
                        )}
                    </div>
                    <div className="flex items-end gap-2">
                        <span className="text-2xl font-bold text-text-pri">{value}</span>
                        {change && (
                            <span className={cn(
                                "text-xs font-medium px-1.5 py-0.5 rounded",
                                changeType === 'positive' && "text-success bg-success/10",
                                changeType === 'negative' && "text-danger bg-danger/10",
                                changeType === 'neutral' && "text-text-sec bg-surface-alt"
                            )}>
                                {changeType === 'positive' && '+'}
                                {change}
                            </span>
                        )}
                    </div>
                </>
            )}
        </motion.div>
    );
}

export default KPICard;
