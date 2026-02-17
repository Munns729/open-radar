import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button'; // Assuming Button exists, or I'll check
import { Badge } from '@/components/ui/Badge';
import { Calculator, ArrowRight, Building2, TrendingUp, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function ValuationCalculator() {
    const [inputs, setInputs] = useState({
        revenue: '',
        ebitda: '',
        sector: 'TMT'
    });
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const calculateValuation = async () => {
        if (!inputs.revenue && !inputs.ebitda) {
            setError("Please provide at least Revenue or EBITDA.");
            return;
        }
        setError(null);
        setLoading(true);

        try {
            // Convert inputs (Millions to Units)
            const rev = inputs.revenue ? parseFloat(inputs.revenue) * 1000000 : null;
            const ebitda = inputs.ebitda ? parseFloat(inputs.ebitda) * 1000000 : null;

            const params = new URLSearchParams();
            if (rev) params.append('revenue_gbp', rev);
            if (ebitda) params.append('ebitda_gbp', ebitda);
            if (inputs.sector) params.append('sector', inputs.sector);
            params.append('geography', 'UK'); // Default to UK

            const res = await fetch(`/api/intelligence/valuation?${params.toString()}`);
            if (res.ok) {
                const data = await res.json();
                setResult(data);
            } else {
                setError("Failed to calculate valuation. Please try again.");
            }
        } catch (err) {
            console.error(err);
            setError("An unexpected error occurred.");
        } finally {
            setLoading(false);
        }
    };

    const formatCurrency = (val) => {
        if (!val) return '£0';
        return `£${(val / 1000000).toFixed(1)}M`;
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Input Section */}
            <Card className="bg-surface border-border-subtle lg:col-span-1 h-fit">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Calculator className="h-5 w-5 text-primary" />
                        Calculator Inputs
                    </CardTitle>
                    <CardDescription>
                        Enter financial data to estimate valuation based on recent market comparables.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-text-sec">Sector</label>
                        <select
                            className="w-full h-10 rounded-md border border-border-subtle bg-surface-alt px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                            value={inputs.sector}
                            onChange={(e) => setInputs({ ...inputs, sector: e.target.value })}
                        >
                            <option value="TMT">TMT</option>
                            <option value="Healthcare">Healthcare</option>
                            <option value="Industrial">Industrial</option>
                            <option value="Consumer">Consumer</option>
                            <option value="Services">Services</option>
                        </select>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-text-sec">Revenue (GBP Millions)</label>
                        <Input
                            type="number"
                            placeholder="e.g. 10.5"
                            value={inputs.revenue}
                            onChange={(e) => setInputs({ ...inputs, revenue: e.target.value })}
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-text-sec">EBITDA (GBP Millions)</label>
                        <Input
                            type="number"
                            placeholder="e.g. 2.5"
                            value={inputs.ebitda}
                            onChange={(e) => setInputs({ ...inputs, ebitda: e.target.value })}
                        />
                    </div>

                    {error && (
                        <div className="text-sm text-danger flex items-center gap-2 bg-danger/10 p-2 rounded">
                            <AlertCircle className="h-4 w-4" />
                            {error}
                        </div>
                    )}

                    <button
                        className="w-full bg-primary text-white py-2 rounded-md font-medium hover:bg-primary/90 transition-colors flex justify-center items-center"
                        onClick={calculateValuation}
                        disabled={loading}
                    >
                        {loading ? 'Calculating...' : 'Calculate Valuation'}
                    </button>

                    <p className="text-xs text-text-ter text-center">
                        Estimates are based on {result?.comparable_count || 0} comparable transactions in our database.
                    </p>
                </CardContent>
            </Card>

            {/* Results Section */}
            <div className="lg:col-span-2 space-y-6">
                {result ? (
                    <>
                        <Card className="bg-surface border-border-subtle overflow-hidden">
                            <div className="p-1 h-2 w-full bg-gradient-to-r from-success to-primary"></div>
                            <CardHeader>
                                <CardTitle className="text-xl">Valuation Estimate</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-3 gap-4 mb-8">
                                    <div className="text-center p-4 bg-surface-alt rounded-lg border border-border-subtle">
                                        <p className="text-sm text-text-sec mb-1">Conservative (Low)</p>
                                        <p className="text-xl md:text-2xl font-bold text-text-pri">{formatCurrency(result.low)}</p>
                                    </div>
                                    <div className="text-center p-4 bg-primary/5 rounded-lg border border-primary/20 scale-105 shadow-sm z-10">
                                        <p className="text-sm text-primary font-medium mb-1">Median Estimate</p>
                                        <p className="text-2xl md:text-3xl font-bold text-primary">{formatCurrency(result.median)}</p>
                                    </div>
                                    <div className="text-center p-4 bg-surface-alt rounded-lg border border-border-subtle">
                                        <p className="text-sm text-text-sec mb-1">Optimistic (High)</p>
                                        <p className="text-xl md:text-2xl font-bold text-text-pri">{formatCurrency(result.high)}</p>
                                    </div>
                                </div>

                                {/* Methods Breakdown */}
                                {result.methods?.length > 0 && (
                                    <div className="space-y-3">
                                        <h4 className="text-sm font-medium text-text-sec uppercase tracking-wide">Methodology</h4>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            {result.methods.map((method, idx) => (
                                                <div key={idx} className="flex justify-between items-center p-3 bg-surface-alt rounded border border-border-subtle text-sm">
                                                    <span className="font-medium text-text-pri capitalize">
                                                        {method.method.replace('_', '/')} Multiple
                                                    </span>
                                                    <div className="text-right">
                                                        <span className="text-text-pri font-mono block">{method.multiples?.median}x</span>
                                                        <span className="text-xs text-text-ter">Median</span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </CardContent>
                        </Card>

                        {/* Comparables Used */}
                        <Card className="bg-surface border-border-subtle">
                            <CardHeader>
                                <CardTitle className="text-lg">Reference Transactions</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-1">
                                    {result.comparables?.map((comp, idx) => (
                                        <div key={idx} className="flex items-center justify-between p-3 hover:bg-surface-alt rounded transition-colors border-b border-border-subtle last:border-0">
                                            <div className="flex items-center gap-3">
                                                <div className="bg-primary/10 p-2 rounded-full">
                                                    <Building2 className="h-4 w-4 text-primary" />
                                                </div>
                                                <div>
                                                    <p className="font-medium text-text-pri">{comp.name}</p>
                                                    <p className="text-xs text-text-sec">{comp.date ? new Date(comp.date).toLocaleDateString() : 'N/A'}</p>
                                                </div>
                                            </div>
                                            <div className="flex gap-4 text-sm font-mono text-text-sec">
                                                {comp.ev_ebitda && (
                                                    <div className="text-right">
                                                        <span className="block text-text-pri">{comp.ev_ebitda.toFixed(1)}x</span>
                                                        <span className="text-[10px] uppercase">EBITDA</span>
                                                    </div>
                                                )}
                                                {comp.ev_revenue && (
                                                    <div className="text-right">
                                                        <span className="block text-text-pri">{comp.ev_revenue.toFixed(1)}x</span>
                                                        <span className="text-[10px] uppercase">Rev</span>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    </>
                ) : (
                    <div className="h-full flex flex-col items-center justify-center p-8 text-center text-text-ter border-2 border-dashed border-border-subtle rounded-lg">
                        <TrendingUp className="h-12 w-12 mb-4 opacity-50" />
                        <h3 className="text-lg font-medium text-text-sec">Ready to Calculate</h3>
                        <p className="max-w-xs mt-2">Enter financial details to see accurate valuation estimates based on market data.</p>
                    </div>
                )}
            </div>
        </div>
    );
}
