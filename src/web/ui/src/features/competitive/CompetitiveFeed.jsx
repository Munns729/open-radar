import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { AlertTriangle, TrendingUp, ExternalLink, Calendar, Building, Filter, ChevronRight } from 'lucide-react';

export default function CompetitiveFeed() {
    const [feed, setFeed] = useState([]);
    const [firms, setFirms] = useState([]);
    const [selectedFirm, setSelectedFirm] = useState(null);
    const [loading, setLoading] = useState(true);
    const [loadingFeed, setLoadingFeed] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchInitialData = async () => {
            try {
                console.log("Fetching competitive data...");
                const [feedData, firmsData] = await Promise.all([
                    api.getCompetitiveFeed(),
                    api.getCompetitiveFirms()
                ]);

                console.log("Feed Data:", feedData);
                console.log("Firms Data:", firmsData);

                if (!Array.isArray(firmsData)) {
                    console.error("Firms data is not an array:", firmsData);
                    throw new Error("Invalid firms data format");
                }

                setFeed(Array.isArray(feedData) ? feedData : []);
                setFirms(Array.isArray(firmsData) ? firmsData : []);
            } catch (error) {
                console.error("Failed to fetch competitive data", error);
                setError(error.message);
            } finally {
                setLoading(false);
            }
        };
        fetchInitialData();
    }, []);

    const handleSelectFirm = async (firm) => {
        setSelectedFirm(firm);
        setLoadingFeed(true);
        try {
            const data = await api.getCompetitiveFeed(firm ? { firm_id: firm.id } : {});
            setFeed(Array.isArray(data) ? data : []);
        } catch (error) {
            console.error("Failed to fetch filtered feed", error);
        } finally {
            setLoadingFeed(false);
        }
    };

    if (error) {
        return (
            <div className="p-8 text-center">
                <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-foreground">Error Loading Competitive Data</h3>
                <p className="text-muted-foreground mt-2">{error}</p>
                <button
                    onClick={() => window.location.reload()}
                    className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
                >
                    Retry
                </button>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[calc(100vh-100px)]">
            {/* Sidebar: Investment Firms */}
            <Card className="lg:col-span-1 border-border/50 bg-card/60 backdrop-blur-xl shadow-xl flex flex-col h-full overflow-hidden">
                <CardHeader className="pb-3 border-b border-border/40">
                    <CardTitle className="flex items-center gap-2 text-lg">
                        <Building className="h-4 w-4 text-primary" />
                        Investment Firms
                    </CardTitle>
                </CardHeader>
                <div className="flex-1 overflow-y-auto p-2 space-y-1">
                    <button
                        onClick={() => handleSelectFirm(null)}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center justify-between group ${!selectedFirm
                            ? 'bg-primary/10 text-primary font-medium'
                            : 'text-muted-foreground hover:bg-muted/50'
                            }`}
                    >
                        <span>All Updates</span>
                        {!selectedFirm && <ChevronRight className="h-3 w-3" />}
                    </button>

                    {firms.map(firm => (
                        <button
                            key={firm.id}
                            onClick={() => handleSelectFirm(firm)}
                            className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex flex-col gap-1 group border border-transparent ${selectedFirm?.id === firm.id
                                ? 'bg-primary/10 border-primary/20 text-foreground'
                                : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
                                }`}
                        >
                            <div className="flex items-center justify-between w-full">
                                <span className={`font-medium ${selectedFirm?.id === firm.id ? 'text-primary' : ''}`}>
                                    {firm.name}
                                </span>
                                {firm.threat_count > 0 && (
                                    <Badge variant="outline" className="text-[10px] h-5 px-1.5 gap-0.5 bg-background/50">
                                        {firm.threat_count}
                                    </Badge>
                                )}
                            </div>
                            <div className="flex items-center justify-between w-full text-xs opacity-80">
                                <span>{firm.tier || 'Uncategorized'}</span>
                                <span>{new Date(firm.last_activity).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
                            </div>
                        </button>
                    ))}
                </div>
            </Card>

            {/* Main Content: Feed */}
            <div className="lg:col-span-3 flex flex-col gap-6 h-full overflow-hidden">
                {/* Firm Detail Header (if selected) */}
                {selectedFirm && (
                    <Card className="border-border/50 bg-card/60 backdrop-blur-xl shrink-0">
                        <CardContent className="p-6">
                            <div className="flex justify-between items-start">
                                <div>
                                    <h2 className="text-2xl font-bold text-foreground mb-1">{selectedFirm.name}</h2>
                                    <div className="flex items-center gap-3 text-sm text-muted-foreground">
                                        <Badge variant="secondary" className="rounded-md">Tier {selectedFirm.tier}</Badge>
                                        <span>•</span>
                                        <span>Last Active: {new Date(selectedFirm.last_activity).toLocaleDateString()}</span>
                                        <span>•</span>
                                        <span>{selectedFirm.focus_sectors || 'Generalist'}</span>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div className="text-sm text-muted-foreground">Total Alerts</div>
                                    <div className="text-2xl font-bold text-primary">{selectedFirm.threat_count}</div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Feed List */}
                <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl flex-1 flex flex-col overflow-hidden">
                    <CardHeader className="shrink-0 pb-4 border-b border-border/40">
                        <CardTitle className="flex items-center gap-2">
                            <TrendingUp className="h-5 w-5 text-accent-main" />
                            {selectedFirm ? `${selectedFirm.name} Activity` : 'All Competitive Intelligence'}
                        </CardTitle>
                        <CardDescription>
                            {selectedFirm
                                ? `Showing latest moves and announcements from ${selectedFirm.name}`
                                : 'Real-time tracking of VC announcements and competitive threats across all firms.'
                            }
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
                        {loading || loadingFeed ? (
                            <div className="flex flex-col items-center justify-center h-40 space-y-2">
                                <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                                <p className="text-sm text-muted-foreground">Loading feed...</p>
                            </div>
                        ) : feed.length === 0 ? (
                            <div className="text-center py-12 flex flex-col items-center">
                                <div className="w-12 h-12 rounded-full bg-muted/50 flex items-center justify-center mb-3">
                                    <Filter className="h-6 w-6 text-muted-foreground" />
                                </div>
                                <p className="text-foreground font-medium">No activity found</p>
                                <p className="text-sm text-muted-foreground mt-1 max-w-xs">{selectedFirm ? `No recorded moves for ${selectedFirm.name} yet.` : 'No competitive intelligence yet.'}</p>
                            </div>
                        ) : (
                            feed.map((item) => (
                                <div
                                    key={item.id}
                                    className="p-4 rounded-xl border border-border/40 bg-background/40 hover:bg-background/60 transition-colors"
                                >
                                    <div className="flex justify-between items-start mb-2">
                                        <div className="flex items-center gap-2">
                                            <Badge variant={
                                                item.threat_level === 'critical' ? 'destructive' :
                                                    item.threat_level === 'high' ? 'destructive' :
                                                        item.threat_level === 'medium' ? 'warning' : 'secondary'
                                            }>
                                                {item.threat_level ? item.threat_level.toUpperCase() : 'UNKNOWN'} THREAT
                                            </Badge>
                                            <span className="text-xs text-muted-foreground flex items-center gap-1">
                                                <Calendar className="h-3 w-3" />
                                                {new Date(item.date).toLocaleDateString()}
                                            </span>
                                        </div>
                                        <button className="text-muted-foreground hover:text-primary transition-colors">
                                            <ExternalLink className="h-4 w-4" />
                                        </button>
                                    </div>

                                    <h4 className="text-lg font-semibold text-foreground mb-1">
                                        {item.company} <span className="text-muted-foreground font-normal">invested in by</span> {item.competitor}
                                    </h4>

                                    <p className="text-sm text-muted-foreground leading-relaxed">
                                        {item.description}
                                    </p>

                                    <div className="mt-3 flex items-center gap-2">
                                        <div className={`text-xs font-medium px-2 py-1 rounded ${item.score >= 80 ? 'text-red-400 bg-red-950/30' :
                                            item.score >= 50 ? 'text-orange-400 bg-orange-950/30' :
                                                'text-indigo-400 bg-indigo-950/30'
                                            }`}>
                                            Threat Score: {item.score}/100
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
