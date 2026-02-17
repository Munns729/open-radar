/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['"DM Sans"', 'sans-serif'],
            },
            colors: {
                background: "var(--page-bg)",
                surface: "var(--surface)",
                "surface-alt": "var(--surface-alt)",
                "surface-hover": "var(--surface-hover)",

                border: "var(--border-main)",
                "border-subtle": "var(--border-subtle)",

                "text-pri": "var(--text-pri)",
                "text-sec": "var(--text-sec)",
                "text-ter": "var(--text-ter)",

                "thead-bg": "var(--thead-bg)",
                "accent-main": "var(--accent-orange)",

                // Primary blue
                primary: {
                    DEFAULT: "var(--primary)",
                    hover: "var(--primary-hover)",
                    light: "var(--primary-light)",
                    dark: "var(--primary-dark)",
                },

                // Semantic colors
                success: {
                    DEFAULT: "var(--success)",
                    light: "var(--success-light)",
                    bg: "var(--success-bg)",
                },
                warning: {
                    DEFAULT: "var(--warning)",
                    light: "var(--warning-light)",
                    bg: "var(--warning-bg)",
                },
                danger: {
                    DEFAULT: "var(--danger)",
                    light: "var(--danger-light)",
                    bg: "var(--danger-bg)",
                },

                priority: {
                    hot: {
                        text: "var(--priority-hot-text)",
                        bg: "var(--priority-hot-bg)",
                        border: "var(--priority-hot-border)",
                    },
                    high: {
                        text: "var(--priority-high-text)",
                        bg: "var(--priority-high-bg)",
                        border: "var(--priority-high-border)",
                    },
                    med: {
                        text: "var(--priority-med-text)",
                        bg: "var(--priority-med-bg)",
                        border: "var(--priority-med-border)",
                    },
                    low: {
                        text: "var(--priority-low-text)",
                        bg: "var(--priority-low-bg)",
                        border: "var(--priority-low-border)",
                    }
                }
            },
            spacing: {
                'sidebar': 'var(--sidebar-width)',
                'sidebar-collapsed': 'var(--sidebar-collapsed-width)',
                'topbar': 'var(--topbar-height)',
            },
            width: {
                'sidebar': 'var(--sidebar-width)',
                'sidebar-collapsed': 'var(--sidebar-collapsed-width)',
            },
            borderRadius: {
                lg: "8px",
                md: "6px",
                sm: "4px",
            },
            transitionDuration: {
                '250': '250ms',
            },
        },
    },
    plugins: [],
}
