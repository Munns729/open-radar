import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Share2, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

// Note: This component uses a simple canvas-based force-directed graph
// For production, consider using react-force-graph-2d or d3-force

const NODE_COLORS = {
    founder: '#a855f7',      // purple
    ceo: '#6366f1',          // indigo
    cfo: '#0ea5e9',          // sky
    advisor: '#10b981',      // emerald
    banker: '#f59e0b',       // amber
    lawyer: '#64748b',       // slate
    investor: '#f43f5e'      // rose
};

const STRENGTH_COLORS = {
    cold: '#3b82f6',
    warm: '#f59e0b',
    hot: '#ef4444'
};

export default function NetworkGraph({ onSelectContact }) {
    const canvasRef = useRef(null);
    const containerRef = useRef(null);
    const [networkData, setNetworkData] = useState({ nodes: [], edges: [], stats: {} });
    const [loading, setLoading] = useState(true);
    const [zoom, setZoom] = useState(1);
    const [hoveredNode, setHoveredNode] = useState(null);
    const [selectedNode, setSelectedNode] = useState(null);
    const nodesRef = useRef([]);
    const edgesRef = useRef([]);
    const animationRef = useRef(null);

    const fetchNetworkData = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/relationships/network-map');
            const data = await res.json();
            setNetworkData(data);
            initializeSimulation(data.nodes, data.edges);
        } catch (error) {
            console.error("Failed to fetch network data", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchNetworkData();
        return () => {
            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current);
            }
        };
    }, []);

    const initializeSimulation = useCallback((nodes, edges) => {
        if (!containerRef.current) return;

        const width = containerRef.current.clientWidth;
        const height = 500;

        // Initialize node positions randomly
        nodesRef.current = nodes.map((node, i) => ({
            ...node,
            x: width / 2 + (Math.random() - 0.5) * width * 0.6,
            y: height / 2 + (Math.random() - 0.5) * height * 0.6,
            vx: 0,
            vy: 0,
            radius: Math.max(8, node.score / 5)
        }));

        edgesRef.current = edges.map(edge => ({
            ...edge,
            sourceNode: nodesRef.current.find(n => n.id === edge.source),
            targetNode: nodesRef.current.find(n => n.id === edge.target)
        }));

        // Start simulation
        runSimulation(width, height);
    }, []);

    const runSimulation = (width, height) => {
        const alpha = 0.1;
        const alphaDecay = 0.99;
        let currentAlpha = 1;

        const simulate = () => {
            if (currentAlpha < 0.01) {
                // Simulation settled, just render
                render(width, height);
                animationRef.current = requestAnimationFrame(simulate);
                return;
            }

            currentAlpha *= alphaDecay;
            const nodes = nodesRef.current;
            const edges = edgesRef.current;

            // Apply forces
            // 1. Repulsion between nodes
            for (let i = 0; i < nodes.length; i++) {
                for (let j = i + 1; j < nodes.length; j++) {
                    const dx = nodes[j].x - nodes[i].x;
                    const dy = nodes[j].y - nodes[i].y;
                    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                    const force = (100 * currentAlpha) / dist;

                    nodes[i].vx -= (dx / dist) * force;
                    nodes[i].vy -= (dy / dist) * force;
                    nodes[j].vx += (dx / dist) * force;
                    nodes[j].vy += (dy / dist) * force;
                }
            }

            // 2. Attraction along edges
            for (const edge of edges) {
                if (!edge.sourceNode || !edge.targetNode) continue;

                const dx = edge.targetNode.x - edge.sourceNode.x;
                const dy = edge.targetNode.y - edge.sourceNode.y;
                const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                const force = dist * 0.01 * currentAlpha;

                edge.sourceNode.vx += (dx / dist) * force;
                edge.sourceNode.vy += (dy / dist) * force;
                edge.targetNode.vx -= (dx / dist) * force;
                edge.targetNode.vy -= (dy / dist) * force;
            }

            // 3. Center gravity
            for (const node of nodes) {
                node.vx += (width / 2 - node.x) * 0.01 * currentAlpha;
                node.vy += (height / 2 - node.y) * 0.01 * currentAlpha;
            }

            // Apply velocity
            for (const node of nodes) {
                node.vx *= 0.9;
                node.vy *= 0.9;
                node.x += node.vx;
                node.y += node.vy;

                // Bound to canvas
                node.x = Math.max(node.radius, Math.min(width - node.radius, node.x));
                node.y = Math.max(node.radius, Math.min(height - node.radius, node.y));
            }

            render(width, height);
            animationRef.current = requestAnimationFrame(simulate);
        };

        simulate();
    };

    const render = (width, height) => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, width, height);

        ctx.save();
        ctx.scale(zoom, zoom);

        const nodes = nodesRef.current;
        const edges = edgesRef.current;

        // Draw edges
        for (const edge of edges) {
            if (!edge.sourceNode || !edge.targetNode) continue;

            ctx.beginPath();
            ctx.moveTo(edge.sourceNode.x, edge.sourceNode.y);
            ctx.lineTo(edge.targetNode.x, edge.targetNode.y);
            ctx.strokeStyle = `rgba(148, 163, 184, ${edge.strength / 100})`;
            ctx.lineWidth = Math.max(1, edge.strength / 30);
            ctx.stroke();
        }

        // Draw nodes
        for (const node of nodes) {
            const isHovered = hoveredNode === node.id;
            const isSelected = selectedNode === node.id;

            ctx.beginPath();
            ctx.arc(node.x, node.y, node.radius * (isHovered || isSelected ? 1.3 : 1), 0, Math.PI * 2);
            ctx.fillStyle = NODE_COLORS[node.type] || '#6b7280';
            ctx.fill();

            if (isSelected) {
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 3;
                ctx.stroke();
            } else if (isHovered) {
                ctx.strokeStyle = STRENGTH_COLORS[node.strength] || '#ffffff';
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            // Draw name for larger nodes or hovered
            if (node.radius > 12 || isHovered || isSelected) {
                ctx.font = `${isHovered || isSelected ? 'bold ' : ''}11px Inter, sans-serif`;
                ctx.fillStyle = '#ffffff';
                ctx.textAlign = 'center';
                ctx.fillText(node.name.split(' ')[0], node.x, node.y + node.radius + 14);
            }
        }

        ctx.restore();
    };

    const handleCanvasClick = (e) => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) / zoom;
        const y = (e.clientY - rect.top) / zoom;

        // Find clicked node
        for (const node of nodesRef.current) {
            const dx = x - node.x;
            const dy = y - node.y;
            const dist = Math.sqrt(dx * dx + dy * dy);

            if (dist < node.radius * 1.5) {
                setSelectedNode(node.id);
                if (onSelectContact) {
                    onSelectContact(node.id);
                }
                return;
            }
        }

        setSelectedNode(null);
    };

    const handleCanvasMouseMove = (e) => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) / zoom;
        const y = (e.clientY - rect.top) / zoom;

        // Find hovered node
        for (const node of nodesRef.current) {
            const dx = x - node.x;
            const dy = y - node.y;
            const dist = Math.sqrt(dx * dx + dy * dy);

            if (dist < node.radius * 1.5) {
                setHoveredNode(node.id);
                canvas.style.cursor = 'pointer';
                return;
            }
        }

        setHoveredNode(null);
        canvas.style.cursor = 'default';
    };

    return (
        <Card className="border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <Share2 className="h-5 w-5 text-cyan-400" />
                            Network Graph
                        </CardTitle>
                        <CardDescription>
                            Visualize your professional network connections.
                        </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setZoom(z => Math.max(0.5, z - 0.25))}
                            className="p-2 hover:bg-muted rounded-lg transition-colors"
                            title="Zoom Out"
                        >
                            <ZoomOut className="h-4 w-4" />
                        </button>
                        <span className="text-sm text-muted-foreground">{Math.round(zoom * 100)}%</span>
                        <button
                            onClick={() => setZoom(z => Math.min(2, z + 0.25))}
                            className="p-2 hover:bg-muted rounded-lg transition-colors"
                            title="Zoom In"
                        >
                            <ZoomIn className="h-4 w-4" />
                        </button>
                        <button
                            onClick={() => setZoom(1)}
                            className="p-2 hover:bg-muted rounded-lg transition-colors"
                            title="Reset Zoom"
                        >
                            <Maximize2 className="h-4 w-4" />
                        </button>
                    </div>
                </div>
            </CardHeader>

            <CardContent>
                {loading ? (
                    <div className="flex items-center justify-center h-[500px]">
                        <p className="text-muted-foreground">Loading network...</p>
                    </div>
                ) : networkData.nodes.length === 0 ? (
                    <div className="flex items-center justify-center h-[500px]">
                        <div className="text-center">
                            <Share2 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                            <p className="text-muted-foreground">No connections to display.</p>
                            <p className="text-sm text-muted-foreground">Add contacts and create connections to see your network.</p>
                        </div>
                    </div>
                ) : (
                    <>
                        <div
                            ref={containerRef}
                            className="border border-border/50 rounded-lg bg-background/50 overflow-hidden"
                        >
                            <canvas
                                ref={canvasRef}
                                width={containerRef.current?.clientWidth || 800}
                                height={500}
                                onClick={handleCanvasClick}
                                onMouseMove={handleCanvasMouseMove}
                                className="w-full"
                            />
                        </div>

                        {/* Legend */}
                        <div className="flex flex-wrap gap-4 mt-4 justify-center">
                            {Object.entries(NODE_COLORS).map(([type, color]) => (
                                <div key={type} className="flex items-center gap-2">
                                    <div
                                        className="w-3 h-3 rounded-full"
                                        style={{ backgroundColor: color }}
                                    />
                                    <span className="text-xs text-muted-foreground capitalize">{type}</span>
                                </div>
                            ))}
                        </div>

                        {/* Stats */}
                        <div className="grid grid-cols-4 gap-4 mt-4">
                            <div className="p-3 border border-border/50 rounded-lg bg-background/50 text-center">
                                <p className="text-2xl font-bold text-cyan-400">{networkData.stats.total_contacts || 0}</p>
                                <p className="text-xs text-muted-foreground">Contacts</p>
                            </div>
                            <div className="p-3 border border-border/50 rounded-lg bg-background/50 text-center">
                                <p className="text-2xl font-bold text-purple-400">{networkData.stats.total_connections || 0}</p>
                                <p className="text-xs text-muted-foreground">Connections</p>
                            </div>
                            <div className="p-3 border border-border/50 rounded-lg bg-background/50 text-center">
                                <p className="text-2xl font-bold text-amber-400">{networkData.stats.hot_contacts || 0}</p>
                                <p className="text-xs text-muted-foreground">Hot Contacts</p>
                            </div>
                            <div className="p-3 border border-border/50 rounded-lg bg-background/50 text-center">
                                <p className="text-2xl font-bold text-green-400">{networkData.stats.avg_connections_per_contact || 0}</p>
                                <p className="text-xs text-muted-foreground">Avg Connections</p>
                            </div>
                        </div>
                    </>
                )}
            </CardContent>
        </Card>
    );
}
