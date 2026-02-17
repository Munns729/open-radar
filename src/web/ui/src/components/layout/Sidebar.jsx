import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import {
    Radar,
    LayoutDashboard,
    Globe,
    Target,
    Lightbulb,
    Radio,
    Newspaper,
    Briefcase,
    Users,
    Coins,
    Split,
    FlaskConical,
    FileText,
    ChevronDown,
    ChevronLeft,
    ChevronRight,
    Settings,
    Menu,
    X,
    Share2
} from 'lucide-react';

const NAV_SECTIONS = [
    {
        id: 'dashboard',
        label: 'Dashboard',
        icon: LayoutDashboard,
        path: '/',
        items: []
    },
    {
        id: 'intelligence',
        label: 'Intelligence',
        icon: Lightbulb,
        items: [
            { id: 'universe', label: 'Universe Scanner', icon: Globe, path: '/universe' },
            { id: 'tracker', label: 'Target Tracker', icon: Target, path: '/tracker' },
            { id: 'deals', label: 'Deal Intelligence', icon: Briefcase, path: '/intelligence' },
        ]
    },
    {
        id: 'monitoring',
        label: 'Monitoring',
        icon: Radio,
        items: [
            { id: 'competitive', label: 'Competitive Radar', icon: Radio, path: '/competitive' },
            { id: 'intel', label: 'Market Intel', icon: Newspaper, path: '/intel' },
            { id: 'portfolio', label: 'Portfolio', icon: Briefcase, path: '/portfolio' },
        ]
    },
    {
        id: 'network',
        label: 'Network',
        icon: Users,
        items: [
            { id: 'network_map', label: 'Network Graph', icon: Share2, path: '/network' },
            { id: 'relationships', label: 'Relationships', icon: Users, path: '/relationships' },
            { id: 'capital', label: 'Capital Flows', icon: Coins, path: '/capital' },
            { id: 'carveout', label: 'Carveouts', icon: Split, path: '/carveout' },
        ]
    },
    {
        id: 'tools',
        label: 'Tools',
        icon: FlaskConical,
        items: [
            { id: 'thesis', label: 'Thesis Validator', icon: FlaskConical, path: '/thesis' },
            { id: 'reports', label: 'Reports', icon: FileText, path: '/reports' },
        ]
    }
];

function NavItem({ item, collapsed, onClick }) {
    const location = useLocation();
    const isActive = location.pathname === item.path;
    const Icon = item.icon;

    return (
        <NavLink
            to={item.path}
            onClick={onClick}
            className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
                isActive
                    ? "bg-primary/10 text-primary"
                    : "text-text-sec hover:text-text-pri hover:bg-surface-hover"
            )}
        >
            <Icon className="h-4 w-4 flex-shrink-0" />
            {!collapsed && (
                <motion.span
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }}
                    className="whitespace-nowrap overflow-hidden"
                >
                    {item.label}
                </motion.span>
            )}
        </NavLink>
    );
}

function NavSection({ section, collapsed, expandedSections, toggleSection, onItemClick }) {
    const location = useLocation();
    const isExpanded = expandedSections.includes(section.id);
    const hasActiveChild = section.items.some(item => location.pathname === item.path);
    const SectionIcon = section.icon;

    // If section has a direct path (like Dashboard), render as single item
    if (section.path) {
        return (
            <NavItem item={section} collapsed={collapsed} onClick={onItemClick} />
        );
    }

    return (
        <div className="space-y-1">
            <button
                onClick={() => toggleSection(section.id)}
                className={cn(
                    "w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
                    hasActiveChild
                        ? "bg-primary/5 text-primary"
                        : "text-text-sec hover:text-text-pri hover:bg-surface-hover"
                )}
            >
                <div className="flex items-center gap-3">
                    <SectionIcon className="h-4 w-4 flex-shrink-0" />
                    {!collapsed && (
                        <motion.span
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="whitespace-nowrap"
                        >
                            {section.label}
                        </motion.span>
                    )}
                </div>
                {!collapsed && (
                    <motion.div
                        animate={{ rotate: isExpanded ? 180 : 0 }}
                        transition={{ duration: 0.2 }}
                    >
                        <ChevronDown className="h-4 w-4" />
                    </motion.div>
                )}
            </button>

            <AnimatePresence>
                {isExpanded && !collapsed && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="pl-4 space-y-1 overflow-hidden"
                    >
                        {section.items.map((item) => (
                            <NavItem key={item.id} item={item} collapsed={collapsed} onClick={onItemClick} />
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

export function Sidebar({ collapsed, onCollapsedChange, mobileOpen, onMobileClose }) {
    const [expandedSections, setExpandedSections] = useState(['intelligence', 'monitoring']);

    const toggleSection = (sectionId) => {
        setExpandedSections(prev =>
            prev.includes(sectionId)
                ? prev.filter(id => id !== sectionId)
                : [...prev, sectionId]
        );
    };

    const sidebarContent = (
        <>
            {/* Logo */}
            <div className="flex h-16 items-center justify-between px-4 border-b border-border-subtle">
                <div className="flex items-center gap-2">
                    <Radar className="h-6 w-6 text-primary" />
                    {!collapsed && (
                        <motion.span
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="text-lg font-bold tracking-wider text-text-pri"
                        >
                            RADAR
                        </motion.span>
                    )}
                </div>
                {/* Close button for mobile */}
                <button
                    onClick={onMobileClose}
                    className="lg:hidden p-2 rounded-lg hover:bg-surface-hover text-text-sec"
                >
                    <X className="h-5 w-5" />
                </button>
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-4 px-3 space-y-2 overflow-y-auto">
                {NAV_SECTIONS.map((section) => (
                    <NavSection
                        key={section.id}
                        section={section}
                        collapsed={collapsed}
                        expandedSections={expandedSections}
                        toggleSection={toggleSection}
                        onItemClick={onMobileClose}
                    />
                ))}
            </nav>

            {/* Footer */}
            <div className="p-3 border-t border-border-subtle">
                <button
                    onClick={() => onCollapsedChange(!collapsed)}
                    className="hidden lg:flex w-full items-center gap-3 px-3 py-2 text-sm font-medium text-text-sec hover:text-text-pri hover:bg-surface-hover rounded-lg transition-colors"
                >
                    {collapsed ? (
                        <ChevronRight className="h-4 w-4" />
                    ) : (
                        <>
                            <ChevronLeft className="h-4 w-4" />
                            <span>Collapse</span>
                        </>
                    )}
                </button>
                <NavLink
                    to="/settings"
                    className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-text-sec hover:text-text-pri hover:bg-surface-hover rounded-lg transition-colors"
                >
                    <Settings className="h-4 w-4" />
                    {!collapsed && <span>Settings</span>}
                </NavLink>
            </div>
        </>
    );

    return (
        <>
            {/* Desktop Sidebar */}
            <motion.aside
                initial={false}
                animate={{ width: collapsed ? 'var(--sidebar-collapsed-width)' : 'var(--sidebar-width)' }}
                transition={{ duration: 0.25, ease: 'easeInOut' }}
                className="hidden lg:flex flex-col border-r border-border-subtle bg-surface h-screen sticky top-0"
            >
                {sidebarContent}
            </motion.aside>

            {/* Mobile Sidebar Overlay */}
            <AnimatePresence>
                {mobileOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="lg:hidden fixed inset-0 bg-black/60 z-40"
                            onClick={onMobileClose}
                        />
                        <motion.aside
                            initial={{ x: '-100%' }}
                            animate={{ x: 0 }}
                            exit={{ x: '-100%' }}
                            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                            className="lg:hidden fixed left-0 top-0 bottom-0 w-64 flex flex-col bg-surface border-r border-border-subtle z-50"
                        >
                            {sidebarContent}
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>
        </>
    );
}

export default Sidebar;
