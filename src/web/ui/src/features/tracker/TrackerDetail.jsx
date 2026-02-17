import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import { ArrowLeft, Building2, Calendar, Link as LinkIcon, AlertTriangle, CheckCircle, Search, MessageSquare, LayoutDashboard } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import NotesPanel from './NotesPanel';
import AgentChat from './AgentChat';

export default function TrackerDetail() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview'); // 'overview' or 'agent'

    const fetchDetail = async () => {
        try {
            const data = await api.getTrackedCompany(id);
            setData(data);
        } catch (error) {
            console.error("Failed to fetch detail", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDetail();
    }, [id]);

    if (loading) return <div className="p-8 text-center text-text-sec">Loading details...</div>;
    if (!data) return <div className="p-8 text-center text-danger">Tracked company not found.</div>;

    const { tracking, profile, events, notes } = data;

    return (
        <div className="space-y-6 h-full flex flex-col">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <Button variant="ghost" className="pl-0 mb-2 hover:bg-transparent text-text-sec hover:text-primary" onClick={() => navigate('/tracker')}>
                        <ArrowLeft className="h-4 w-4 mr-1" />
                        Back to Tracker
                    </Button>
                    <h1 className="text-3xl font-bold text-text-pri flex items-center gap-3">
                        {profile?.name || 'Loading Name...'}
                        <Badge className="text-base capitalize bg-primary/10 text-primary border-primary/20">
                            {tracking.priority} Priority
                        </Badge>
                    </h1>
                    <div className="flex gap-4 mt-2 text-sm text-text-sec">
                        <span className="flex items-center gap-1">
                            <Building2 className="h-4 w-4" />
                            {profile?.sector || 'Unknown Sector'}
                        </span>
                        <span className="flex items-center gap-1">
                            <Calendar className="h-4 w-4" />
                            Added {new Date(tracking.added_date).toLocaleDateString()}
                        </span>
                    </div>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" className="text-danger border-danger/20 hover:bg-danger/10">Stop Tracking</Button>
                </div>
            </div>

            {/* Tabs Navigation */}
            <div className="flex border-b border-border-subtle">
                <button
                    onClick={() => setActiveTab('overview')}
                    className={cn(
                        "px-6 py-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2",
                        activeTab === 'overview'
                            ? "border-primary text-primary"
                            : "border-transparent text-text-sec hover:text-text-pri"
                    )}
                >
                    <LayoutDashboard className="h-4 w-4" />
                    Target Overview
                </button>
                <button
                    onClick={() => setActiveTab('agent')}
                    className={cn(
                        "px-6 py-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2",
                        activeTab === 'agent'
                            ? "border-primary text-primary"
                            : "border-transparent text-text-sec hover:text-text-pri"
                    )}
                >
                    <MessageSquare className="h-4 w-4" />
                    Radar Agent
                </button>
            </div>

            {/* Main Content Grid */}
            <div className="flex-1 min-h-0">
                {activeTab === 'overview' ? (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full min-h-0">
                        {/* Left Column: Overview & Events */}
                        <div className="lg:col-span-2 space-y-6 overflow-y-auto pr-2 scrollbar-hide">
                            {/* Key Stats / Tags */}
                            <Card>
                                <CardHeader>
                                    <CardTitle>Overview</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div>
                                        <h3 className="text-sm font-medium text-text-sec mb-2">Investment Thesis Tags</h3>
                                        <div className="flex flex-wrap gap-2">
                                            {tracking.tags?.map((tag, i) => (
                                                <Badge key={i} variant="secondary">{tag}</Badge>
                                            ))}
                                            {(!tracking.tags || tracking.tags.length === 0) && (
                                                <span className="text-sm text-text-ter italic">No tags added.</span>
                                            )}
                                        </div>
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-medium text-text-sec mb-1">Tracking Notes</h3>
                                        <p className="text-text-pri">{tracking.notes || "No initial notes provided."}</p>
                                    </div>
                                </CardContent>
                            </Card>

                            {/* Events Timeline */}
                            <Card>
                                <CardHeader>
                                    <CardTitle>Timeline</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    {events.length === 0 ? (
                                        <div className="text-center text-text-ter py-8">No events recorded yet.</div>
                                    ) : (
                                        <div className="space-y-6 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-border-subtle before:to-transparent">
                                            {events.map((event, idx) => (
                                                <div key={event.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                                                    <div className="flex items-center justify-center w-10 h-10 rounded-full border border-border bg-surface shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2">
                                                        {event.event_type === 'funding' && <CheckCircle className="w-5 h-5 text-success" />}
                                                        {event.event_type === 'leadership' && <AlertTriangle className="w-5 h-5 text-warning" />}
                                                        {event.event_type === 'news' && <LinkIcon className="w-5 h-5 text-primary" />}
                                                    </div>
                                                    <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded bg-surface-alt border border-border-subtle shadow-sm">
                                                        <div className="flex items-center justify-between space-x-2 mb-1">
                                                            <div className="font-bold text-text-pri">{event.title}</div>
                                                            <time className="font-mono text-xs text-text-ter">{event.event_date}</time>
                                                        </div>
                                                        <div className="text-text-sec text-sm">{event.description}</div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        </div>

                        {/* Right Column: Interactive Notes */}
                        <div className="lg:col-span-1 h-full min-h-0">
                            <NotesPanel
                                notes={notes}
                                trackedId={tracking.id}
                                onNoteAdded={fetchDetail}
                            />
                        </div>
                    </div>
                ) : (
                    <AgentChat trackedId={tracking.id} companyName={profile?.name} />
                )}
            </div>
        </div>
    );
}
