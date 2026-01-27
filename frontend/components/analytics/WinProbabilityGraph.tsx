import React from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    ReferenceLine
} from 'recharts';
import { Trophy } from 'lucide-react';

interface WinProbabilityGraphProps {
    data: { trick: number; us: number }[];
}

export const WinProbabilityGraph: React.FC<WinProbabilityGraphProps> = ({ data }) => {
    // Filter valid data points
    const chartData = data.map(d => ({
        name: `Trick ${d.trick}`,
        prob: (d.us * 100).toFixed(1), // Convert to percentage
        raw: d.us
    }));

    if (chartData.length === 0) {
        return (
            <div className="w-full h-full flex items-center justify-center text-white/50 text-sm">
                No Data Yet
            </div>
        );
    }

    return (
        <div className="w-full h-full p-4 bg-slate-900/90 rounded-xl border border-white/10 backdrop-blur-md shadow-2xl flex flex-col">
            <div className="flex items-center justify-between mb-2">
                <h3 className="text-yellow-500 font-bold text-sm flex items-center gap-2">
                    <Trophy size={14} /> Win Probability
                </h3>
                <span className="text-xs text-white/60">Live Heuristic</span>
            </div>

            <div className="flex-1 min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#444" vertical={false} />
                        <XAxis
                            dataKey="name"
                            hide={true}
                        />
                        <YAxis
                            domain={[0, 100]}
                            hide={false}
                            stroke="#888"
                            tick={{ fontSize: 10 }}
                            width={30}
                        />
                        <ReferenceLine y={50} stroke="#666" strokeDasharray="5 5" />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#1e293b', borderColor: '#d97706', color: '#fff' }}
                            itemStyle={{ color: '#fbbf24' }}
                            labelStyle={{ display: 'none' }}
                            formatter={(value: any) => [`${value}%`, 'Win Chance']}
                        />
                        <Line
                            type="monotone"
                            dataKey="prob"
                            stroke="#fbbf24"
                            strokeWidth={3}
                            dot={{ r: 3, fill: '#fbbf24' }}
                            activeDot={{ r: 6, stroke: '#fff' }}
                            animationDuration={500}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};
