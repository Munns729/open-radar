import { Menu } from 'lucide-react';
import CurrencySelector from '../CurrencySelector';
import GlobalSearch from '../GlobalSearch';

export default function TopBar({ onMenuClick, pageTitle }) {
    return (
        <header className="h-topbar flex items-center justify-between px-6 border-b border-border-subtle bg-surface/80 backdrop-blur-md sticky top-0 z-40">
            {/* Left section */}
            <div className="flex items-center gap-4">
                <button
                    onClick={onMenuClick}
                    className="lg:hidden p-2 rounded-lg hover:bg-surface-hover text-text-sec hover:text-text-pri transition-colors"
                    aria-label="Toggle menu"
                >
                    <Menu className="h-5 w-5" />
                </button>
                {pageTitle && (
                    <h1 className="text-lg font-semibold text-text-pri hidden sm:block">
                        {pageTitle}
                    </h1>
                )}
            </div>

            {/* Center - Global Search */}
            <div className="flex-1 flex justify-center max-w-xl mx-4">
                <GlobalSearch />
            </div>

            {/* Right section - placeholder for user menu */}
            <div className="flex items-center gap-3">
                <CurrencySelector />
                <div className="h-5 w-px bg-border-subtle mx-1" />
                <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center text-primary text-sm font-medium">
                    R
                </div>
            </div>
        </header>
    );
}
