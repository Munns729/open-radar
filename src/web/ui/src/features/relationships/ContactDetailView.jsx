import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { User, Mail, Phone, MapPin, Briefcase, MessageSquare, Network, Lightbulb, ArrowLeft, Plus, ExternalLink } from 'lucide-react';

const INTERACTION_TYPES = ['email', 'call', 'meeting', 'linkedin_message'];
const OUTCOMES = ['positive', 'neutral', 'negative', 'no_response'];

const strengthColors = {
    cold: 'from-blue-500 to-cyan-500',
    warm: 'from-amber-500 to-orange-500',
    hot: 'from-red-500 to-pink-500'
};

export default function ContactDetailView({ contactId, onBack }) {
    const [activeTab, setActiveTab] = useState('profile');
    const [contact, setContact] = useState(null);
    const [interactions, setInteractions] = useState([]);
    const [connections, setConnections] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showInteractionModal, setShowInteractionModal] = useState(false);
    const [newInteraction, setNewInteraction] = useState({
        contact_id: contactId,
        interaction_type: 'email',
        interaction_date: new Date().toISOString().split('T')[0],
        subject: '',
        notes: '',
        outcome: '',
        next_action: '',
        next_action_date: ''
    });

    const fetchContactDetail = async () => {
        setLoading(true);
        try {
            const res = await fetch(`/api/relationships/contact/${contactId}`);
            const data = await res.json();
            setContact(data.contact);
            setInteractions(data.interactions || []);
            setConnections(data.connections || []);
        } catch (error) {
            console.error("Failed to fetch contact detail", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (contactId) {
            fetchContactDetail();
        }
    }, [contactId]);

    const handleLogInteraction = async (e) => {
        e.preventDefault();
        try {
            const res = await fetch('/api/relationships/interaction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...newInteraction,
                    contact_id: contactId
                })
            });

            if (res.ok) {
                setShowInteractionModal(false);
                setNewInteraction({
                    contact_id: contactId,
                    interaction_type: 'email',
                    interaction_date: new Date().toISOString().split('T')[0],
                    subject: '',
                    notes: '',
                    outcome: '',
                    next_action: '',
                    next_action_date: ''
                });
                fetchContactDetail();
            }
        } catch (error) {
            console.error("Error logging interaction", error);
        }
    };

    if (loading) {
        return (
            <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl">
                <CardContent className="flex items-center justify-center h-64">
                    <p className="text-muted-foreground">Loading contact details...</p>
                </CardContent>
            </Card>
        );
    }

    if (!contact) {
        return (
            <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl">
                <CardContent className="flex items-center justify-center h-64">
                    <p className="text-muted-foreground">Contact not found</p>
                </CardContent>
            </Card>
        );
    }

    const tabs = [
        { id: 'profile', label: 'Profile', icon: User },
        { id: 'interactions', label: 'Interactions', icon: MessageSquare },
        { id: 'network', label: 'Network', icon: Network },
        { id: 'insights', label: 'Insights', icon: Lightbulb }
    ];

    return (
        <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={onBack}
                            className="p-2 hover:bg-muted rounded-lg transition-colors"
                        >
                            <ArrowLeft className="h-5 w-5" />
                        </button>
                        <div>
                            <CardTitle className="text-2xl">{contact.full_name}</CardTitle>
                            <p className="text-muted-foreground">
                                {contact.job_title} {contact.company_name && `at ${contact.company_name}`}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className={`px-3 py-1 rounded-full text-sm font-medium bg-gradient-to-r ${strengthColors[contact.relationship_strength]} text-white`}>
                            {contact.relationship_strength.toUpperCase()}
                        </div>
                        <div className="text-sm text-muted-foreground">
                            Score: <span className="font-bold text-foreground">{contact.relationship_score}</span>/100
                        </div>
                    </div>
                </div>

                {/* Tabs */}
                <div className="flex gap-1 mt-6 border-b border-border">
                    {tabs.map(tab => (
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
            </CardHeader>

            <CardContent>
                {/* Profile Tab */}
                {activeTab === 'profile' && (
                    <div className="grid grid-cols-2 gap-6">
                        <div className="space-y-4">
                            <h3 className="font-semibold text-lg mb-4">Contact Information</h3>

                            <div className="flex items-center gap-3">
                                <Mail className="h-4 w-4 text-muted-foreground" />
                                <span>{contact.email || 'No email'}</span>
                            </div>

                            <div className="flex items-center gap-3">
                                <Phone className="h-4 w-4 text-muted-foreground" />
                                <span>{contact.phone || 'No phone'}</span>
                            </div>

                            <div className="flex items-center gap-3">
                                <MapPin className="h-4 w-4 text-muted-foreground" />
                                <span>{contact.location || 'No location'}</span>
                            </div>

                            <div className="flex items-center gap-3">
                                <Briefcase className="h-4 w-4 text-muted-foreground" />
                                <span className="capitalize">{contact.contact_type}</span>
                            </div>

                            {contact.linkedin_url && (
                                <a
                                    href={contact.linkedin_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-2 text-blue-400 hover:text-blue-300"
                                >
                                    <ExternalLink className="h-4 w-4" />
                                    LinkedIn Profile
                                </a>
                            )}
                        </div>

                        <div className="space-y-4">
                            <h3 className="font-semibold text-lg mb-4">Notes</h3>
                            <p className="text-muted-foreground whitespace-pre-wrap">
                                {contact.notes || 'No notes added yet.'}
                            </p>

                            {contact.tags && contact.tags.length > 0 && (
                                <div>
                                    <h4 className="font-medium mb-2">Tags</h4>
                                    <div className="flex gap-2 flex-wrap">
                                        {contact.tags.map((tag, i) => (
                                            <span key={i} className="px-2 py-1 bg-muted rounded text-sm">
                                                {tag}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div className="pt-4 border-t border-border">
                                <p className="text-xs text-muted-foreground">
                                    Created: {new Date(contact.created_at).toLocaleDateString()}
                                </p>
                                {contact.last_contact_date && (
                                    <p className="text-xs text-muted-foreground">
                                        Last Contact: {new Date(contact.last_contact_date).toLocaleDateString()}
                                    </p>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* Interactions Tab */}
                {activeTab === 'interactions' && (
                    <div>
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="font-semibold text-lg">Interaction History</h3>
                            <button
                                onClick={() => setShowInteractionModal(true)}
                                className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                            >
                                <Plus className="h-4 w-4" />
                                Log Interaction
                            </button>
                        </div>

                        {interactions.length === 0 ? (
                            <p className="text-muted-foreground text-center py-8">
                                No interactions recorded yet. Log your first interaction!
                            </p>
                        ) : (
                            <div className="space-y-4">
                                {interactions.map(interaction => (
                                    <div
                                        key={interaction.id}
                                        className="p-4 border border-border/50 rounded-lg bg-background/50"
                                    >
                                        <div className="flex justify-between items-start mb-2">
                                            <div className="flex items-center gap-2">
                                                <span className="px-2 py-1 bg-purple-500/20 text-purple-300 rounded text-xs uppercase">
                                                    {interaction.interaction_type.replace('_', ' ')}
                                                </span>
                                                {interaction.outcome && (
                                                    <span className={`px-2 py-1 rounded text-xs capitalize ${interaction.outcome === 'positive' ? 'bg-green-500/20 text-green-300' :
                                                            interaction.outcome === 'negative' ? 'bg-red-500/20 text-red-300' :
                                                                interaction.outcome === 'no_response' ? 'bg-gray-500/20 text-gray-300' :
                                                                    'bg-amber-500/20 text-amber-300'
                                                        }`}>
                                                        {interaction.outcome.replace('_', ' ')}
                                                    </span>
                                                )}
                                            </div>
                                            <span className="text-xs text-muted-foreground">
                                                {new Date(interaction.interaction_date).toLocaleDateString()}
                                            </span>
                                        </div>
                                        {interaction.subject && (
                                            <p className="font-medium mb-1">{interaction.subject}</p>
                                        )}
                                        {interaction.notes && (
                                            <p className="text-sm text-muted-foreground">{interaction.notes}</p>
                                        )}
                                        {interaction.next_action && (
                                            <div className="mt-2 pt-2 border-t border-border/50">
                                                <p className="text-xs text-amber-400">
                                                    Next: {interaction.next_action}
                                                    {interaction.next_action_date && ` (${new Date(interaction.next_action_date).toLocaleDateString()})`}
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Network Tab */}
                {activeTab === 'network' && (
                    <div>
                        <h3 className="font-semibold text-lg mb-4">Connected Contacts</h3>

                        {connections.length === 0 ? (
                            <p className="text-muted-foreground text-center py-8">
                                No connections recorded for this contact.
                            </p>
                        ) : (
                            <div className="grid grid-cols-2 gap-4">
                                {connections.map(conn => (
                                    <div
                                        key={conn.id}
                                        className="p-4 border border-border/50 rounded-lg bg-background/50 hover:border-purple-500/50 transition-colors"
                                    >
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <p className="font-medium">{conn.other_contact_name}</p>
                                                <p className="text-sm text-muted-foreground">{conn.other_contact_company}</p>
                                            </div>
                                            <span className="text-xs px-2 py-1 bg-muted rounded capitalize">
                                                {conn.connection_type.replace('_', ' ')}
                                            </span>
                                        </div>
                                        <div className="mt-3 flex items-center gap-2">
                                            <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"
                                                    style={{ width: `${conn.strength}%` }}
                                                />
                                            </div>
                                            <span className="text-xs text-muted-foreground">{conn.strength}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Insights Tab */}
                {activeTab === 'insights' && (
                    <div className="space-y-6">
                        <div>
                            <h3 className="font-semibold text-lg mb-4">Relationship Strength</h3>
                            <div className="p-4 border border-border/50 rounded-lg bg-background/50">
                                <div className="flex items-center justify-between mb-2">
                                    <span>Score</span>
                                    <span className="font-bold text-2xl">{contact.relationship_score}/100</span>
                                </div>
                                <div className="h-4 bg-gray-700 rounded-full overflow-hidden">
                                    <div
                                        className={`h-full bg-gradient-to-r ${strengthColors[contact.relationship_strength]} rounded-full transition-all`}
                                        style={{ width: `${contact.relationship_score}%` }}
                                    />
                                </div>
                                <p className="text-sm text-muted-foreground mt-2">
                                    Based on interaction frequency, recency, and outcomes.
                                </p>
                            </div>
                        </div>

                        <div>
                            <h3 className="font-semibold text-lg mb-4">Suggested Actions</h3>
                            <div className="space-y-3">
                                {contact.last_contact_date && (
                                    (() => {
                                        const daysSince = Math.floor((new Date() - new Date(contact.last_contact_date)) / (1000 * 60 * 60 * 24));
                                        if (daysSince > 90) {
                                            return (
                                                <div className="p-3 border border-amber-500/50 rounded-lg bg-amber-500/10">
                                                    <p className="text-amber-300 font-medium">⚠️ Follow-up Needed</p>
                                                    <p className="text-sm text-muted-foreground">
                                                        It's been {daysSince} days since your last interaction.
                                                    </p>
                                                </div>
                                            );
                                        }
                                        return null;
                                    })()
                                )}

                                {!contact.linkedin_url && (
                                    <div className="p-3 border border-blue-500/50 rounded-lg bg-blue-500/10">
                                        <p className="text-blue-300 font-medium">💡 Add LinkedIn Profile</p>
                                        <p className="text-sm text-muted-foreground">
                                            Add their LinkedIn URL to enable profile enrichment.
                                        </p>
                                    </div>
                                )}

                                {interactions.length < 3 && (
                                    <div className="p-3 border border-purple-500/50 rounded-lg bg-purple-500/10">
                                        <p className="text-purple-300 font-medium">📈 Build Relationship</p>
                                        <p className="text-sm text-muted-foreground">
                                            Log more interactions to improve your relationship score.
                                        </p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </CardContent>

            {/* Log Interaction Modal */}
            {showInteractionModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="bg-card border border-border rounded-xl p-6 w-full max-w-lg">
                        <h2 className="text-xl font-semibold mb-4">Log Interaction</h2>
                        <form onSubmit={handleLogInteraction} className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium mb-1">Type</label>
                                    <select
                                        value={newInteraction.interaction_type}
                                        onChange={(e) => setNewInteraction({ ...newInteraction, interaction_type: e.target.value })}
                                        className="w-full px-3 py-2 bg-background border border-border rounded-lg"
                                    >
                                        {INTERACTION_TYPES.map(type => (
                                            <option key={type} value={type}>
                                                {type.replace('_', ' ').charAt(0).toUpperCase() + type.replace('_', ' ').slice(1)}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Date</label>
                                    <input
                                        type="date"
                                        value={newInteraction.interaction_date}
                                        onChange={(e) => setNewInteraction({ ...newInteraction, interaction_date: e.target.value })}
                                        className="w-full px-3 py-2 bg-background border border-border rounded-lg"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Subject</label>
                                <input
                                    type="text"
                                    value={newInteraction.subject}
                                    onChange={(e) => setNewInteraction({ ...newInteraction, subject: e.target.value })}
                                    className="w-full px-3 py-2 bg-background border border-border rounded-lg"
                                    placeholder="Brief description of the interaction"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Notes</label>
                                <textarea
                                    value={newInteraction.notes}
                                    onChange={(e) => setNewInteraction({ ...newInteraction, notes: e.target.value })}
                                    className="w-full px-3 py-2 bg-background border border-border rounded-lg"
                                    rows={3}
                                    placeholder="Details about what was discussed..."
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Outcome</label>
                                <select
                                    value={newInteraction.outcome}
                                    onChange={(e) => setNewInteraction({ ...newInteraction, outcome: e.target.value })}
                                    className="w-full px-3 py-2 bg-background border border-border rounded-lg"
                                >
                                    <option value="">Select outcome...</option>
                                    {OUTCOMES.map(outcome => (
                                        <option key={outcome} value={outcome}>
                                            {outcome.replace('_', ' ').charAt(0).toUpperCase() + outcome.replace('_', ' ').slice(1)}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium mb-1">Next Action</label>
                                    <input
                                        type="text"
                                        value={newInteraction.next_action}
                                        onChange={(e) => setNewInteraction({ ...newInteraction, next_action: e.target.value })}
                                        className="w-full px-3 py-2 bg-background border border-border rounded-lg"
                                        placeholder="Follow up with..."
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Due Date</label>
                                    <input
                                        type="date"
                                        value={newInteraction.next_action_date}
                                        onChange={(e) => setNewInteraction({ ...newInteraction, next_action_date: e.target.value })}
                                        className="w-full px-3 py-2 bg-background border border-border rounded-lg"
                                    />
                                </div>
                            </div>
                            <div className="flex gap-3 justify-end">
                                <button
                                    type="button"
                                    onClick={() => setShowInteractionModal(false)}
                                    className="px-4 py-2 text-muted-foreground hover:text-foreground transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                                >
                                    Log Interaction
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </Card>
    );
}
