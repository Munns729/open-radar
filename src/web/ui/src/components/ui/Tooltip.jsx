import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';

export function TooltipProvider({ children }) {
    return <>{children}</>;
}

export function Tooltip({ children, delayDuration = 200 }) {
    const [open, setOpen] = useState(false);
    const [coords, setCoords] = useState({ x: 0, y: 0 });
    const triggerRef = useRef(null);
    const timeoutRef = useRef(null);

    const handleMouseEnter = () => {
        timeoutRef.current = setTimeout(() => {
            if (triggerRef.current) {
                const rect = triggerRef.current.getBoundingClientRect();
                setCoords({
                    x: rect.left + rect.width / 2,
                    y: rect.top,
                });
                setOpen(true);
            }
        }, delayDuration);
    };

    const handleMouseLeave = () => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        setOpen(false);
    };

    return (
        <div
            className="inline-block"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            ref={triggerRef}
        >
            {React.Children.map(children, child => {
                if (child.type === TooltipTrigger) {
                    return child;
                }
                if (child.type === TooltipContent && open) {
                    return <TooltipPortal coords={coords}>{child.props.children}</TooltipPortal>;
                }
                return null;
            })}
        </div>
    );
}

export function TooltipTrigger({ children, asChild }) {
    return <>{children}</>;
}

export function TooltipContent({ children }) {
    return <>{children}</>;
}

function TooltipPortal({ children, coords }) {
    return createPortal(
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 5 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 5 }}
                style={{
                    position: 'fixed',
                    left: coords.x,
                    top: coords.y,
                    transform: 'translate(-50%, -100%)',
                    zIndex: 9999,
                    pointerEvents: 'none',
                    paddingBottom: '8px',
                }}
            >
                <div className="bg-popover text-popover-foreground px-3 py-1.5 text-sm rounded-md border border-border shadow-md whitespace-normal break-words max-w-xs transition-colors">
                    {children}
                </div>
            </motion.div>
        </AnimatePresence>,
        document.body
    );
}
