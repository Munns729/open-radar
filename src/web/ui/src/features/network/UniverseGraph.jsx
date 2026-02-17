import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Share2, ZoomIn, ZoomOut, Maximize2, Filter, Loader2 } from 'lucide-react';

const UniverseGraph = () => {
    const graphRef = useRef();
    const [graphData, setGraphData] = useState({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({
        country: '',
        min_moat: '',
        limit: 50
    });

    const [dimensions, setDimensions] = useState({ w: 800, h: 600 });
    const containerRef = useRef(null);

    // Filter Options
    const countries = ["FR", "DE", "NL", "BE", "GB", "US"];

    const fetchGraphData = async () => {
        setLoading(true);
        try {
            const data = await api.getUniverseGraph(filters);

            // Process data for graph
            // ForceGraph expects mutable objects, so we verify structure
            setGraphData(data || { nodes: [], links: [] });
        } catch (error) {
            console.error("Failed to fetch universe graph", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchGraphData();
    }, [filters]);

    useEffect(() => {
        // Resize observer
        if (!containerRef.current) return;
        const resizeObserver = new ResizeObserver(entries => {
            const { width, height } = entries[0].contentRect;
            setDimensions({ w: width, h: height });
        });
        resizeObserver.observe(containerRef.current);
        return () => resizeObserver.disconnect();
    }, []);

    const handleNodeClick = useCallback(node => {
        // Center view on node
        graphRef.current.centerAt(node.x, node.y, 1000);
        graphRef.current.zoom(3, 2000);
    }, []);

    const handleFilterChange = (key, value) => {
        setFilters(prev => ({ ...prev, [key]: value }));
    };

    return (
        <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl h-full flex flex-col">
            <CardHeader className="pb-4">
                <div className="flex items-center justify-between flex-wrap gap-4">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <Share2 className="h-5 w-5 text-purple-400" />
                            Universe Network
                        </CardTitle>
                        <CardDescription>
                            Visualizing Hub (Known) & Spoke (Discovered) Companies
                        </CardDescription>
                    </div>

                    {/* Filters Toolbar */}
                    <div className="flex items-center gap-2 bg-background/50 p-1 rounded-md border border-border/50">
                        <Filter className="h-4 w-4 text-muted-foreground ml-2" />

                        <select
                            className="bg-transparent text-sm border-none focus:ring-0 text-foreground"
                            value={filters.country}
                            onChange={(e) => handleFilterChange('country', e.target.value)}
                        >
                            <option value="">All Countries</option>
                            {countries.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>

                        <select
                            className="bg-transparent text-sm border-none focus:ring-0 text-foreground"
                            value={filters.min_moat}
                            onChange={(e) => handleFilterChange('min_moat', e.target.value)}
                        >
                            <option value="">Any Moat</option>
                            <option value="50">Moat 50+</option>
                            <option value="70">Moat 70+</option>
                        </select>

                        <select
                            className="bg-transparent text-sm border-none focus:ring-0 text-foreground"
                            value={filters.limit}
                            onChange={(e) => handleFilterChange('limit', e.target.value)}
                        >
                            <option value="50">50 Nodes</option>
                            <option value="100">100 Nodes</option>
                            <option value="200">200 Nodes</option>
                        </select>
                    </div>
                </div>
            </CardHeader>

            <CardContent className="flex-1 p-0 relative min-h-[500px]" ref={containerRef}>
                {loading && (
                    <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/50 backdrop-blur-sm">
                        <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
                    </div>
                )}

                {!loading && graphData.nodes.length === 0 && (
                    <div className="absolute inset-0 z-10 flex items-center justify-center">
                        <p className="text-muted-foreground">No companies found for these filters.</p>
                    </div>
                )}

                <ForceGraph2D
                    ref={graphRef}
                    width={dimensions.w}
                    height={dimensions.h}
                    graphData={graphData}
                    nodeLabel="name"
                    nodeColor={node => node.color}
                    nodeRelSize={6}
                    linkColor={() => "rgba(100, 116, 139, 0.2)"}
                    linkWidth={1}
                    linkDirectionalArrowLength={3.5}
                    linkDirectionalArrowRelPos={1}
                    onNodeClick={handleNodeClick}
                    cooldownTicks={100}
                    onEngineStop={() => graphRef.current.zoomToFit(400)}
                />

                {/* Legend Overlay */}
                <div className="absolute bottom-4 left-4 bg-background/80 p-2 rounded-md border border-border/50 text-xs backdrop-blur-md">
                    <div className="flex items-center gap-2 mb-1">
                        <div className="w-3 h-3 rounded-full bg-purple-500"></div>
                        <span>Hub (Wiki/Seed)</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-slate-500"></div>
                        <span>Spoke (Discovered)</span>
                    </div>
                </div>

                <div className="absolute bottom-4 right-4 flex gap-2">
                    <button
                        onClick={() => graphRef.current.zoomIn()}
                        className="p-2 bg-background/80 border border-border/50 rounded-md hover:bg-muted"
                    >
                        <ZoomIn className="h-4 w-4" />
                    </button>
                    <button
                        onClick={() => graphRef.current.zoomOut()}
                        className="p-2 bg-background/80 border border-border/50 rounded-md hover:bg-muted"
                    >
                        <ZoomOut className="h-4 w-4" />
                    </button>
                    <button
                        onClick={() => graphRef.current.zoomToFit(400)}
                        className="p-2 bg-background/80 border border-border/50 rounded-md hover:bg-muted"
                    >
                        <Maximize2 className="h-4 w-4" />
                    </button>
                </div>
            </CardContent>
        </Card>
    );
};

export default UniverseGraph;
