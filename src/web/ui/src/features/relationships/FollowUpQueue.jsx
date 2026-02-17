import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Clock, AlertTriangle, Mail, Phone, Calendar, CheckCircle } from 'lucide-react';

const urgencyColors = {
    high: 'bg-red-500/20 text-red-300 border-red-500/50',
    medium: 'bg-amber-500/20 text-amber-300 border-amber-500/50',
    low: 'bg-green-500/20 text-green-300 border-green-500/50'
};

export default function FollowUpQueue({ onSelectContact }) {
    const [followUps, setFollowUps] = useState([]);
    const [loading, setLoading] = useState(true);
    const [daysThreshold, setDaysThreshold] = useState(90);

    const fetchFollowUps = async () => {
        setLoading(true);
        try {
            const res = await fetch(`/api/relationships/follow-ups?days_threshold=${daysThreshold}&limit=20`);
            const data = await res.json();
            setFollowUps(data.follow_ups || []);
        } catch (error) {
            console.error("Failed to fetch follow-ups", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchFollowUps();
    }, [daysThreshold]);

    const getUrgency = (daysSinceContact) => {
        if (daysSinceContact > 180) return 'high';
        if (daysSinceContact > 120) return 'medium';
        return 'low';
    };

    const formatDaysAgo = (days) => {
        if (days > 365) {
            const years = Math.floor(days / 365);
            return `${years} year${years > 1 ? 's' : ''} ago`;
        }
        if (days > 30) {
            const months = Math.floor(days / 30);
            return `${months} month${months > 1 ? 's' : ''} ago`;
        }
        return `${days} days ago`;
    };

    const handleMarkComplete = async (contactId) => {
        // Log a quick interaction to mark follow-up complete
        try {
            await fetch('/api/relationships/interaction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contact_id: contactId,
                    interaction_type: 'call',
                    subject: 'Quick check-in',
                    outcome: 'neutral'
                })
            });
            fetchFollowUps();
        } catch (error) {
            console.error("Error marking follow-up complete", error);
        }
    };

    return (
        <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <Clock className="h-5 w-5 text-amber-400" />
                            Follow-Up Queue
                        </CardTitle>
                        <CardDescription>
                            Contacts that need your attention to maintain relationship strength.
                        </CardDescription>
                    </div>
                    <div className="flex items-center gap-3">
                        <label className="text-sm text-muted-foreground">Threshold:</label>
                        <select
                            value={daysThreshold}
                            onChange={(e) => setDaysThreshold(Number(e.target.value))}
                            className="px-3 py-1.5 bg-background/50 border border-border/50 rounded-lg text-sm"
                        >
                            <option value={30}>30 days</option>
                            <option value={60}>60 days</option>
                            <option value={90}>90 days</option>
                            <option value={180}>180 days</option>
                        </select>
                    </div>
                </div>
            </CardHeader>

            <CardContent>
                {loading ? (
                    <div className="flex items-center justify-center h-32">
                        <p className="text-muted-foreground">Loading follow-ups...</p>
                    </div>
                ) : followUps.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-32">
                        <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
                        <p className="text-muted-foreground">All caught up!</p>
                        <p className="text-sm text-muted-foreground mt-1">
                            No contacts need follow-up based on your current threshold.
                        </p>
                    </div>
                ) : (
                    <>
                        {/* Summary */}
                        <div className="grid grid-cols-3 gap-4 mb-6">
                            <div className={`p-3 border rounded-lg ${urgencyColors.high}`}>
                                <p className="text-2xl font-bold">
                                    {followUps.filter(f => getUrgency(f.days_since_contact) === 'high').length}
                                </p>
                                <p className="text-xs">Urgent (&gt;180 days)</p>
                            </div>
                            <div className={`p-3 border rounded-lg ${urgencyColors.medium}`}>
                                <p className="text-2xl font-bold">
                                    {followUps.filter(f => getUrgency(f.days_since_contact) === 'medium').length}
                                </p>
                                <p className="text-xs">Overdue (120-180 days)</p>
                            </div>
                            <div className={`p-3 border rounded-lg ${urgencyColors.low}`}>
                                <p className="text-2xl font-bold">
                                    {followUps.filter(f => getUrgency(f.days_since_contact) === 'low').length}
                                </p>
                                <p className="text-xs">Coming Up (90-120 days)</p>
                            </div>
                        </div>

                        {/* Follow-up List */}
                        <div className="space-y-3">
                            {followUps.map((followUp) => {
                                const urgency = getUrgency(followUp.days_since_contact);

                                return (
                                    <div
                                        key={followUp.contact_id}
                                        className={`p-4 border rounded-lg bg-background/50 hover:bg-background/80 transition-colors ${urgency === 'high' ? 'border-red-500/30' :
                                                urgency === 'medium' ? 'border-amber-500/30' :
                                                    'border-border/50'
                                            }`}
                                    >
                                        <div className="flex items-start justify-between">
                                            <div
                                                className="cursor-pointer flex-1"
                                                onClick={() => onSelectContact && onSelectContact(followUp.contact_id)}
                                            >
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="font-medium">{followUp.contact_name}</span>
                                                    {urgency === 'high' && (
                                                        <AlertTriangle className="h-4 w-4 text-red-400" />
                                                    )}
                                                </div>
                                                <p className="text-sm text-muted-foreground">
                                                    {followUp.company_name && `${followUp.company_name} • `}
                                                    <span className="capitalize">{followUp.contact_type}</span>
                                                </p>
                                                <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                                                    <span className="flex items-center gap-1">
                                                        <Calendar className="h-3 w-3" />
                                                        Last contact: {formatDaysAgo(followUp.days_since_contact)}
                                                    </span>
                                                    <span className={`px-2 py-0.5 rounded ${followUp.relationship_strength === 'hot' ? 'bg-red-500/20 text-red-300' :
                                                            followUp.relationship_strength === 'warm' ? 'bg-amber-500/20 text-amber-300' :
                                                                'bg-blue-500/20 text-blue-300'
                                                        }`}>
                                                        {followUp.relationship_strength}
                                                    </span>
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-2">
                                                {followUp.email && (
                                                    <a
                                                        href={`mailto:${followUp.email}`}
                                                        className="p-2 hover:bg-muted rounded-lg transition-colors"
                                                        title="Send Email"
                                                    >
                                                        <Mail className="h-4 w-4" />
                                                    </a>
                                                )}
                                                {followUp.phone && (
                                                    <a
                                                        href={`tel:${followUp.phone}`}
                                                        className="p-2 hover:bg-muted rounded-lg transition-colors"
                                                        title="Call"
                                                    >
                                                        <Phone className="h-4 w-4" />
                                                    </a>
                                                )}
                                                <button
                                                    onClick={() => handleMarkComplete(followUp.contact_id)}
                                                    className="flex items-center gap-1 px-3 py-1.5 text-xs bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                                                >
                                                    <CheckCircle className="h-3 w-3" />
                                                    Done
                                                </button>
                                            </div>
                                        </div>

                                        {followUp.suggested_action && (
                                            <div className="mt-3 pt-3 border-t border-border/50">
                                                <p className="text-sm text-amber-300">
                                                    💡 {followUp.suggested_action}
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </>
                )}
            </CardContent>
        </Card>
    );
}
