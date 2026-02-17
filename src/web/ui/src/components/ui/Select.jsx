import * as React from "react"
import { cn } from "@/lib/utils"
// Simplified Select for speed, can upgrade to Radix later if needed
const Select = React.forwardRef(({ className, children, ...props }, ref) => {
    return (
        <div className="relative">
            <select
                className={cn(
                    "flex h-9 w-full items-center justify-between rounded-md border border-input bg-surface-alt px-3 py-2 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
                    className
                )}
                ref={ref}
                {...props}
            >
                {children}
            </select>
        </div>
    )
})
Select.displayName = "Select"

export { Select }
