import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Users, Share2, Clock, Sparkles, TrendingUp, UserPlus } from 'lucide-react';

import ContactsList from './ContactsList';
import ContactDetailView from './ContactDetailView';
import WarmIntroFinder from './WarmIntroFinder';
import NetworkGraph from './NetworkGraph';
import FollowUpQueue from './FollowUpQueue';

const TABS = [
    { id: 'overview', label: 'Overview', icon: TrendingUp },
    { id: 'contacts', label: 'Contacts', icon: Users },
    { id: 'network', label: 'Network', icon: Share2 },
    { id: 'warm-intro', label: 'Warm Intros', icon: Sparkles },
    { id: 'follow-ups', label: 'Follow-Ups', icon: Clock }
];

export default function RelationshipsDashboard() {
    const [activeTab, setActiveTab] = useState('overview');
    const [selectedContactId, setSelectedContactId] = useState(null);
    const [stats, setStats] = useState(null);
    const [recentActivity, setRecentActivity] = useState([]);

    const fetchStats = async () => {
        try {
            const res = await fetch('/api/relationships/stats');
            const data = await res.json();
            setStats(data);
        } catch (error) {
            console.error("Failed to fetch relationship stats", error);
        }
    };

    useEffect(() => {
        fetchStats();
    }, []);

    const handleSelectContact = (contactId) => {
        setSelectedContactId(contactId);
        setActiveTab('contact-detail');
    };

    const handleBackToContacts = () => {
        setSelectedContactId(null);
        setActiveTab('contacts');
    };

    // If viewing a contact detail
    if (activeTab === 'contact-detail' && selectedContactId) {
        return (
            <div className="space-y-6">
                <ContactDetailView
                    contactId={selectedContactId}
                    onBack={handleBackToContacts}
                />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header with Tabs */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 via-pink-400 to-amber-400 bg-clip-text text-transparent">
                        Relationship Manager
                    </h1>
                    <p className="text-muted-foreground mt-1">
                        Track and nurture your professional network
                    </p>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 border-b border-border">
                {TABS.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${activeTab === tab.id
                                ? 'border-purple-500 text-purple-400'
                                : 'border-transparent text-muted-foreground hover:text-foreground'
                            }`}
                    >
                        <tab.icon className="h-4 w-4" />
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            {activeTab === 'overview' && (
                <div className="space-y-6">
                    {/* Stats Cards */}
                    <div className="grid grid-cols-4 gap-4">
                        <Card className="border-border/50 bg-card/60 backdrop-blur-xl">
                            <CardContent className="pt-6">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-sm text-muted-foreground">Total Contacts</p>
                                        <p className="text-3xl font-bold text-purple-400">
                                            {stats?.total_contacts || 0}
                                        </p>
                                    </div>
                                    <Users className="h-8 w-8 text-purple-400/50" />
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="border-border/50 bg-card/60 backdrop-blur-xl">
                            <CardContent className="pt-6">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-sm text-muted-foreground">Hot Contacts</p>
                                        <p className="text-3xl font-bold text-red-400">
                                            {stats?.by_strength?.hot || 0}
                                        </p>
                                    </div>
                                    <TrendingUp className="h-8 w-8 text-red-400/50" />
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="border-border/50 bg-card/60 backdrop-blur-xl">
                            <CardContent className="pt-6">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-sm text-muted-foreground">Connections</p>
                                        <p className="text-3xl font-bold text-cyan-400">
                                            {stats?.total_connections || 0}
                                        </p>
                                    </div>
                                    <Share2 className="h-8 w-8 text-cyan-400/50" />
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="border-border/50 bg-card/60 backdrop-blur-xl">
                            <CardContent className="pt-6">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-sm text-muted-foreground">Need Follow-Up</p>
                                        <p className="text-3xl font-bold text-amber-400">
                                            {stats?.needing_followup || 0}
                                        </p>
                                    </div>
                                    <Clock className="h-8 w-8 text-amber-400/50" />
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Contact Type Breakdown */}
                    {stats?.by_type && Object.keys(stats.by_type).length > 0 && (
                        <Card className="border-border/50 bg-card/60 backdrop-blur-xl">
                            <CardHeader>
                                <CardTitle className="text-lg">Contact Types</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex flex-wrap gap-4">
                                    {Object.entries(stats.by_type).map(([type, count]) => (
                                        <div
                                            key={type}
                                            className="flex items-center gap-3 px-4 py-2 bg-muted/50 rounded-lg"
                                        >
                                            <span className="capitalize font-medium">{type}</span>
                                            <span className="text-muted-foreground">{count}</span>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Quick Actions */}
                    <div className="grid grid-cols-3 gap-4">
                        <button
                            onClick={() => setActiveTab('contacts')}
                            className="p-6 border border-border/50 rounded-lg bg-card/60 hover:bg-purple-500/10 hover:border-purple-500/50 transition-colors text-left"
                        >
                            <UserPlus className="h-8 w-8 text-purple-400 mb-3" />
                            <h3 className="font-semibold mb-1">Add Contact</h3>
                            <p className="text-sm text-muted-foreground">
                                Add a new founder, advisor, or deal contact to your network.
                            </p>
                        </button>

                        <button
                            onClick={() => setActiveTab('warm-intro')}
                            className="p-6 border border-border/50 rounded-lg bg-card/60 hover:bg-amber-500/10 hover:border-amber-500/50 transition-colors text-left"
                        >
                            <Sparkles className="h-8 w-8 text-amber-400 mb-3" />
                            <h3 className="font-semibold mb-1">Find Warm Intro</h3>
                            <p className="text-sm text-muted-foreground">
                                Discover the best path to reach any contact through your network.
                            </p>
                        </button>

                        <button
                            onClick={() => setActiveTab('follow-ups')}
                            className="p-6 border border-border/50 rounded-lg bg-card/60 hover:bg-cyan-500/10 hover:border-cyan-500/50 transition-colors text-left"
                        >
                            <Clock className="h-8 w-8 text-cyan-400 mb-3" />
                            <h3 className="font-semibold mb-1">Review Follow-Ups</h3>
                            <p className="text-sm text-muted-foreground">
                                See contacts that need attention to maintain relationship strength.
                            </p>
                        </button>
                    </div>

                    {/* Relationship Strength Distribution */}
                    {stats?.by_strength && (
                        <Card className="border-border/50 bg-card/60 backdrop-blur-xl">
                            <CardHeader>
                                <CardTitle className="text-lg">Relationship Strength Distribution</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex h-8 rounded-full overflow-hidden">
                                    {['hot', 'warm', 'cold'].map(strength => {
                                        const count = stats.by_strength[strength] || 0;
                                        const total = stats.total_contacts || 1;
                                        const percentage = (count / total) * 100;

                                        if (percentage === 0) return null;

                                        const colors = {
                                            hot: 'bg-gradient-to-r from-red-600 to-red-500',
                                            warm: 'bg-gradient-to-r from-amber-600 to-amber-500',
                                            cold: 'bg-gradient-to-r from-blue-600 to-blue-500'
                                        };

                                        return (
                                            <div
                                                key={strength}
                                                className={`${colors[strength]} flex items-center justify-center text-xs font-medium text-white`}
                                                style={{ width: `${percentage}%` }}
                                                title={`${strength}: ${count} (${percentage.toFixed(1)}%)`}
                                            >
                                                {percentage > 10 && `${Math.round(percentage)}%`}
                                            </div>
                                        );
                                    })}
                                </div>
                                <div className="flex justify-center gap-6 mt-4">
                                    <div className="flex items-center gap-2">
                                        <div className="w-3 h-3 rounded-full bg-red-500" />
                                        <span className="text-sm text-muted-foreground">Hot</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="w-3 h-3 rounded-full bg-amber-500" />
                                        <span className="text-sm text-muted-foreground">Warm</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="w-3 h-3 rounded-full bg-blue-500" />
                                        <span className="text-sm text-muted-foreground">Cold</span>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </div>
            )}

            {activeTab === 'contacts' && (
                <ContactsList onSelectContact={handleSelectContact} />
            )}

            {activeTab === 'network' && (
                <NetworkGraph onSelectContact={handleSelectContact} />
            )}

            {activeTab === 'warm-intro' && (
                <WarmIntroFinder />
            )}

            {activeTab === 'follow-ups' && (
                <FollowUpQueue onSelectContact={handleSelectContact} />
            )}
        </div>
    );
}
