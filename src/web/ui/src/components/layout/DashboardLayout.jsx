import React, { useState } from 'react';
import { Sidebar } from './Sidebar';
import TopBar from './TopBar';
import { motion, AnimatePresence } from 'framer-motion';

export function DashboardLayout({ children, pageTitle }) {
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    return (
        <div className="flex min-h-screen bg-background text-text-pri">
            <Sidebar
                collapsed={sidebarCollapsed}
                onCollapsedChange={setSidebarCollapsed}
                mobileOpen={mobileMenuOpen}
                onMobileClose={() => setMobileMenuOpen(false)}
            />

            <div className="flex-1 flex flex-col min-w-0">
                <TopBar
                    onMenuClick={() => setMobileMenuOpen(true)}
                    pageTitle={pageTitle}
                />

                <main className="flex-1 overflow-y-auto">
                    <div className="container mx-auto p-6 max-w-7xl">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={pageTitle}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -10 }}
                                transition={{ duration: 0.2 }}
                            >
                                {children}
                            </motion.div>
                        </AnimatePresence>
                    </div>
                </main>
            </div>
        </div>
    );
}

export default DashboardLayout;
