import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Search, ArrowRight, User, Sparkles, Mail } from 'lucide-react';

const strengthColors = {
    cold: 'border-blue-500 bg-blue-500/20',
    warm: 'border-amber-500 bg-amber-500/20',
    hot: 'border-red-500 bg-red-500/20'
};

export default function WarmIntroFinder() {
    const [searchTerm, setSearchTerm] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [searching, setSearching] = useState(false);
    const [selectedTarget, setSelectedTarget] = useState(null);
    const [introPath, setIntroPath] = useState(null);
    const [loadingPath, setLoadingPath] = useState(false);

    const searchContacts = async () => {
        if (!searchTerm.trim()) return;
        
        setSearching(true);
        try {
            const res = await fetch(`/api/relationships/contacts?search=${encodeURIComponent(searchTerm)}&limit=10`);
            const data = await res.json();
            setSearchResults(data.contacts || []);
        } catch (error) {
            console.error("Search failed", error);
        } finally {
            setSearching(false);
        }
    };

    const findIntroPath = async (contactId) => {
        setSelectedTarget(searchResults.find(c => c.id === contactId));
        setLoadingPath(true);
        setIntroPath(null);
        
        try {
            const res = await fetch(`/api/relationships/warm-intro/${contactId}`);
            const data = await res.json();
            setIntroPath(data);
        } catch (error) {
            console.error("Failed to find intro path", error);
        } finally {
            setLoadingPath(false);
        }
    };

    const generateIntroEmail = () => {
        if (!introPath || !introPath.suggested_introducer || !selectedTarget) return;
        
        const introducer = introPath.suggested_introducer;
        const subject = `Introduction Request: ${selectedTarget.full_name}`;
        const body = `Hi ${introducer.contact_name},

I hope this email finds you well!

I noticed you're connected with ${selectedTarget.full_name}${selectedTarget.company ? ` at ${selectedTarget.company}` : ''}. I'd love to get an introduction if you feel comfortable making one.

[Add context about why you'd like to connect]

Would you be open to making an intro? Happy to provide a forwardable blurb if that helps.

Thanks!`;
        
        // Open default email client
        window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    };

    return (
        <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-amber-400" />
                    Warm Introduction Finder
                </CardTitle>
                <CardDescription>
                    Find the best path to reach a target contact through your network.
                </CardDescription>
            </CardHeader>

            <CardContent className="space-y-6">
                {/* Search */}
                <div className="flex gap-3">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <input
                            type="text"
                            placeholder="Search for a contact to reach..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && searchContacts()}
                            className="w-full pl-10 pr-4 py-3 bg-background/50 border border-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500/50"
                        />
                    </div>
                    <button
                        onClick={searchContacts}
                        disabled={searching}
                        className="px-6 py-3 bg-amber-600 hover:bg-amber-700 text-white rounded-lg transition-colors disabled:opacity-50"
                    >
                        {searching ? 'Searching...' : 'Search'}
                    </button>
                </div>

                {/* Search Results */}
                {searchResults.length > 0 && !introPath && (
                    <div className="space-y-2">
                        <h3 className="text-sm font-medium text-muted-foreground">Select a target contact:</h3>
                        <div className="grid gap-2">
                            {searchResults.map(contact => (
                                <button
                                    key={contact.id}
                                    onClick={() => findIntroPath(contact.id)}
                                    className="flex items-center justify-between p-3 border border-border/50 rounded-lg bg-background/50 hover:border-amber-500/50 transition-colors text-left"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center">
                                            <User className="h-5 w-5 text-muted-foreground" />
                                        </div>
                                        <div>
                                            <p className="font-medium">{contact.full_name}</p>
                                            <p className="text-sm text-muted-foreground">
                                                {contact.job_title} {contact.company_name && `at ${contact.company_name}`}
                                            </p>
                                        </div>
                                    </div>
                                    <div className={`px-2 py-1 rounded text-xs ${strengthColors[contact.relationship_strength]}`}>
                                        {contact.relationship_strength}
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Loading State */}
                {loadingPath && (
                    <div className="text-center py-8">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-500 mx-auto mb-4"></div>
                        <p className="text-muted-foreground">Analyzing your network...</p>
                    </div>
                )}

                {/* Intro Path Result */}
                {introPath && selectedTarget && (
                    <div className="space-y-6">
                        <div className="flex items-center justify-between">
                            <h3 className="font-semibold">Path to {selectedTarget.full_name}</h3>
                            <button
                                onClick={() => {
                                    setIntroPath(null);
                                    setSelectedTarget(null);
                                }}
                                className="text-sm text-muted-foreground hover:text-foreground"
                            >
                                New Search
                            </button>
                        </div>

                        {introPath.success && introPath.path ? (
                            <>
                                {/* Path Visualization */}
                                <div className="p-4 border border-border/50 rounded-lg bg-background/50">
                                    <div className="flex items-center justify-center flex-wrap gap-2">
                                        {introPath.path.map((step, index) => (
                                            <React.Fragment key={step.contact_id}>
                                                <div className={`flex flex-col items-center p-3 rounded-lg ${
                                                    step.is_start ? 'bg-green-500/20 border border-green-500/50' :
                                                    step.is_target ? 'bg-amber-500/20 border border-amber-500/50' :
                                                    'bg-muted'
                                                }`}>
                                                    <div className="w-10 h-10 rounded-full bg-background flex items-center justify-center mb-1">
                                                        <User className="h-5 w-5" />
                                                    </div>
                                                    <span className="text-sm font-medium text-center max-w-[100px] truncate">
                                                        {step.contact_name}
                                                    </span>
                                                    {step.company && (
                                                        <span className="text-xs text-muted-foreground max-w-[100px] truncate">
                                                            {step.company}
                                                        </span>
                                                    )}
                                                    {step.is_start && (
                                                        <span className="text-xs text-green-400 mt-1">You</span>
                                                    )}
                                                    {step.is_target && (
                                                        <span className="text-xs text-amber-400 mt-1">Target</span>
                                                    )}
                                                </div>
                                                
                                                {index < introPath.path.length - 1 && (
                                                    <div className="flex flex-col items-center">
                                                        <ArrowRight className="h-5 w-5 text-muted-foreground" />
                                                        {step.connection_strength && (
                                                            <span className="text-xs text-muted-foreground">
                                                                {introPath.path[index + 1].connection_strength}%
                                                            </span>
                                                        )}
                                                    </div>
                                                )}
                                            </React.Fragment>
                                        ))}
                                    </div>
                                </div>

                                {/* Path Stats */}
                                <div className="grid grid-cols-3 gap-4">
                                    <div className="p-3 border border-border/50 rounded-lg bg-background/50 text-center">
                                        <p className="text-2xl font-bold text-amber-400">{introPath.path_length}</p>
                                        <p className="text-xs text-muted-foreground">Degrees of Separation</p>
                                    </div>
                                    <div className="p-3 border border-border/50 rounded-lg bg-background/50 text-center">
                                        <p className="text-2xl font-bold text-green-400">{introPath.min_link_strength}%</p>
                                        <p className="text-xs text-muted-foreground">Weakest Link</p>
                                    </div>
                                    <div className="p-3 border border-border/50 rounded-lg bg-background/50 text-center">
                                        <p className="text-2xl font-bold text-purple-400">
                                            {introPath.suggested_introducer?.contact_name?.split(' ')[0] || '-'}
                                        </p>
                                        <p className="text-xs text-muted-foreground">Best Introducer</p>
                                    </div>
                                </div>

                                {/* Suggested Introducer */}
                                {introPath.suggested_introducer && (
                                    <div className="p-4 border border-green-500/50 rounded-lg bg-green-500/10">
                                        <h4 className="font-medium text-green-300 mb-2">💡 Suggested Introduction Path</h4>
                                        <p className="text-sm text-muted-foreground mb-3">
                                            Ask <strong>{introPath.suggested_introducer.contact_name}</strong> 
                                            {introPath.suggested_introducer.company && ` (${introPath.suggested_introducer.company})`} 
                                            {' '}to introduce you to {selectedTarget.full_name}.
                                            {introPath.suggested_introducer.connection_strength && (
                                                <span> They have a {introPath.suggested_introducer.connection_strength}% connection strength.</span>
                                            )}
                                        </p>
                                        <button
                                            onClick={generateIntroEmail}
                                            className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                                        >
                                            <Mail className="h-4 w-4" />
                                            Draft Introduction Request
                                        </button>
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="p-6 border border-amber-500/50 rounded-lg bg-amber-500/10 text-center">
                                <p className="text-amber-300 font-medium mb-2">No Warm Path Found</p>
                                <p className="text-sm text-muted-foreground">
                                    {introPath.message || "No connection path exists in your network to this contact."}
                                </p>
                                <p className="text-sm text-muted-foreground mt-2">
                                    {introPath.suggestion || "Consider reaching out directly or finding mutual connections on LinkedIn."}
                                </p>
                            </div>
                        )}
                    </div>
                )}

                {/* Empty State */}
                {!searching && searchResults.length === 0 && !introPath && searchTerm && (
                    <div className="text-center py-8">
                        <p className="text-muted-foreground">No contacts found matching "{searchTerm}"</p>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
