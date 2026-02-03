
import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

interface Node {
    id: string;
    parentId: string | null;
    scoreUs: number;
    scoreThem: number;
    timestamp: string;
    isFork: boolean;
    children?: Node[];
}

interface MultiverseTreeProps {
    onSelectGame: (gameId: string) => void;
    currentGameId: string;
}

const MultiverseTree: React.FC<MultiverseTreeProps> = ({ onSelectGame, currentGameId }) => {
    const svgRef = useRef<SVGSVGElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [nodes, setNodes] = useState<Node[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Fetch Data
    useEffect(() => {
        fetch('/react-py4web/replay/multiverse')
            .then(res => {
                if (!res.ok) throw new Error("Fetch Failed: " + res.statusText);
                return res.json();
            })
            .then(data => {
                if (data.nodes) setNodes(data.nodes);
                else if (data.error) setError(data.error);
                setLoading(false);
            })
            .catch(e => {
                setError(e.message);
                setLoading(false);
            });
    }, []);

    // Render D3 Graph with Zoom
    useEffect(() => {
        if (loading || !svgRef.current || !containerRef.current) return;

        // Fallback or Real Data
        const nodesToUse = nodes.length > 0 ? nodes : [
            { id: "root", parentId: null, scoreUs: 0, scoreThem: 0, timestamp: "0", isFork: false }
        ];

        try {
            const containerWidth = containerRef.current.clientWidth || 800;
            const containerHeight = containerRef.current.clientHeight || 500;
            const margin = { top: 20, right: 120, bottom: 20, left: 120 };

            // Clear previous
            const svg = d3.select(svgRef.current);
            svg.selectAll("*").remove();

            svg.attr("width", "100%")
                .attr("height", "100%")
                .attr("viewBox", `0 0 ${containerWidth} ${containerHeight}`)
                .style("background-color", "rgba(0,0,0,0.2)"); // Visual bounds

            // Zoom Container
            const g = svg.append("g");

            // Build Hierarchy
            const nodeMap = new Map<string, Node>();
            nodesToUse.forEach(n => nodeMap.set(n.id, { ...n, children: [] }));

            const roots: Node[] = [];
            nodeMap.forEach(n => {
                if (n.parentId && nodeMap.has(n.parentId)) {
                    nodeMap.get(n.parentId)!.children!.push(n);
                } else {
                    roots.push(n);
                }
            });

            // Active Root Logic
            let activeRoot = roots.find(r => r.id === currentGameId) || roots[0];
            if (nodeMap.has(currentGameId)) {
                let curr = nodeMap.get(currentGameId);
                while (curr?.parentId && nodeMap.has(curr.parentId)) {
                    curr = nodeMap.get(curr.parentId);
                }
                if (curr) activeRoot = curr;
            }

            if (!activeRoot) {
                g.append("text").text("No Data").attr("fill", "white").attr("y", 100).attr("x", 100);
                return;
            }

            const rootLayout = d3.hierarchy<Node>(activeRoot);

            // Dynamic Tree Size based on depth/breadth
            // If tree is huge, we make the logical layout larger, zoom handles the view
            const levelHeight = 150;
            const nodeHeight = 60;
            const maxDepth = rootLayout.height;
            const maxBreadth = Math.max(1, rootLayout.leaves().length);

            const treeWidth = Math.max(containerWidth - margin.left - margin.right, maxDepth * levelHeight);
            const treeHeight = Math.max(containerHeight - margin.top - margin.bottom, maxBreadth * nodeHeight);

            const treeLayout = d3.tree<Node>()
                .size([treeHeight, treeWidth]); // D3 Tree uses [height, width] for horizontal layout

            treeLayout(rootLayout);

            // Center the tree initially
            const initialTransform = d3.zoomIdentity
                .translate(margin.left, margin.top);

            // Zoom Behavior
            const zoom = d3.zoom<SVGSVGElement, unknown>()
                .scaleExtent([0.1, 3])
                .on("zoom", (event) => {
                    g.attr("transform", event.transform);
                });

            svg.call(zoom)
                .call(zoom.transform, initialTransform);

            // Render Links
            const linkGen = d3.linkHorizontal()
                .x((d: any) => d.y)
                .y((d: any) => d.x) as any;

            g.selectAll('.link')
                .data(rootLayout.links())
                .enter()
                .append('path')
                .attr('class', 'link')
                .attr('d', linkGen)
                .attr('fill', 'none')
                .attr('stroke', '#CDA434')
                .attr('stroke-width', 2)
                .attr('opacity', 0.6);

            // Render Nodes
            const nodeGroup = g.selectAll('.node')
                .data(rootLayout.descendants())
                .enter()
                .append('g')
                .attr('class', d => `node ${d.data.id === currentGameId ? 'active' : ''}`)
                .attr("transform", (d: any) => `translate(${d.y},${d.x})`)
                .style("cursor", "pointer")
                .on("click", (event, d) => onSelectGame(d.data.id));

            // Node Circle
            nodeGroup.append('circle')
                .attr('r', 12)
                .style('fill', (d: any) => {
                    if (d.data.id === currentGameId) return '#CDA434';
                    const win = d.data.scoreUs > d.data.scoreThem;
                    return win ? '#4ade80' : '#f87171'; // Green/Red
                })
                .style('stroke', '#1a1a1a')
                .style('stroke-width', 2);

            // Current Indicator Ring
            g.selectAll('.node.active')
                .append('circle')
                .attr('r', 18)
                .attr('fill', 'none')
                .attr('stroke', '#CDA434')
                .attr('stroke-width', 2)
                .attr('stroke-dasharray', '4 2')
                .style('animation', 'spin 10s linear infinite'); // CSS handle spin if possible, else static

            // Score Labels
            nodeGroup.append('text')
                .attr('dy', '.35em')
                .attr('x', (d: any) => d.children && d.children.length ? -18 : 18)
                .style('text-anchor', (d: any) => d.children && d.children.length ? 'end' : 'start')
                .text((d: any) => `${d.data.scoreUs}-${d.data.scoreThem}`)
                .style('fill', 'white')
                .style('font-size', '12px')
                .style('font-weight', 'bold')
                .style('text-shadow', '0 2px 4px rgba(0,0,0,0.8)');

            // Fork ID Label
            nodeGroup.append('text')
                .attr('dy', '1.6em')
                .attr('x', (d: any) => d.children && d.children.length ? -18 : 18)
                .style('text-anchor', (d: any) => d.children && d.children.length ? 'end' : 'start')
                .text((d: any) => d.data.isFork ? '⚡ fork' : 'root')
                .style('fill', '#CDA434')
                .style('font-size', '8px')
                .style('opacity', 0.8);

        } catch (err: any) {
            console.error(err);
        }

    }, [nodes, loading, currentGameId]);

    return (
        <div ref={containerRef} className="bg-slate-900/90 rounded-2xl border border-white/10 p-1 shadow-2xl relative overflow-hidden w-[90vw] h-[80vh] backdrop-blur-xl">
            <div className="absolute top-4 left-4 z-10 pointer-events-none">
                <h3 className="text-[#CDA434] font-bold text-lg flex items-center gap-2 drop-shadow-md">
                    <span>⚡</span> Multiverse Tree <span className="text-xs text-slate-400 font-normal border border-white/10 px-2 py-0.5 rounded-full">{nodes.length} Timelines</span>
                </h3>
                <p className="text-[10px] text-white/40 mt-1 max-w-[200px]">
                    Scroll to Zoom • Drag to Pan <br />
                    Click node to travel
                </p>
            </div>

            <svg ref={svgRef} className="w-full h-full cursor-grab active:cursor-grabbing"></svg>

            {/* Legend */}
            <div className="absolute bottom-4 right-4 flex gap-4 text-[10px] bg-black/40 px-3 py-1.5 rounded-full border border-white/5 backdrop-blur-md text-white/60 pointer-events-none">
                <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-400"></span> Win</div>
                <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-400"></span> Loss</div>
                <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#CDA434]"></span> Current</div>
            </div>

            {loading && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/50 backdrop-blur-sm z-20">
                    <div className="text-[#CDA434] animate-pulse font-mono">Loading timelines...</div>
                </div>
            )}
        </div>
    );
};

export default MultiverseTree;
