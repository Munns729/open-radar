import React from 'react';
import { motion } from 'framer-motion';
import { Construction } from 'lucide-react';

export default function PlaceholderPage({ title, description }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center h-[calc(100vh-200px)]"
        >
            <div className="p-6 bg-surface border border-border-subtle rounded-2xl text-center max-w-md">
                <div className="p-4 bg-warning/10 rounded-xl inline-block mb-4">
                    <Construction className="h-10 w-10 text-warning" />
                </div>
                <h2 className="text-xl font-semibold text-text-pri mb-2">{title}</h2>
                <p className="text-text-sec text-sm">
                    {description || "This feature is currently under development. Check back soon!"}
                </p>
                <div className="mt-4 flex items-center justify-center gap-2 text-xs text-text-ter">
                    <span className="h-2 w-2 rounded-full bg-warning animate-pulse" />
                    Coming Soon
                </div>
            </div>
        </motion.div>
    );
}
