import React from 'react';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell
} from 'recharts';
import { Flame } from 'lucide-react';

interface BlunderGraphProps {
    data: { [key: string]: number }; // Map "Bottom": 2, "Top": 5 etc
}

export const BlunderGraph: React.FC<BlunderGraphProps> = ({ data }) => {
    // Transform Map to Array for Recharts
    // Ensure all positions are represented 
    const positions = ['Bottom', 'Right', 'Top', 'Left'];
    const chartData = positions.map(pos => ({
        name: pos,
        count: data[pos] || 0
    }));

    const totalBlunders = Object.values(data).reduce((a: number, b: number) => a + b, 0);

    if (totalBlunders === 0) {
        return (
            <div className="w-full h-full flex flex-col items-center justify-center text-white/50 text-sm">
                <Flame size={24} className="mb-2 text-white/20" />
                <span>Clean Game (So Far)</span>
            </div>
        );
    }

    return (
        <div className="w-full h-full p-4 bg-slate-900/90 rounded-xl border border-white/10 backdrop-blur-md shadow-2xl flex flex-col">
            <div className="flex items-center justify-between mb-2">
                <h3 className="text-red-500 font-bold text-sm flex items-center gap-2">
                    <Flame size={14} /> Blunder Heatmap
                </h3>
                <span className="text-xs text-white/60">Total: {totalBlunders}</span>
            </div>

            <div className="flex-1 min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="#444" horizontal={false} />
                        <XAxis type="number" hide />
                        <YAxis
                            dataKey="name"
                            type="category"
                            width={50}
                            tick={{ fill: '#ccc', fontSize: 11 }}
                            axisLine={false}
                            tickLine={false}
                        />
                        <Tooltip
                            cursor={{ fill: 'transparent' }}
                            contentStyle={{ backgroundColor: '#1e293b', borderColor: '#ef4444', color: '#fff' }}
                            itemStyle={{ color: '#fca5a5' }}
                            labelStyle={{ display: 'none' }}
                            formatter={(value: any) => [`${value} Blunders`]}
                        />
                        <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                            {chartData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.name === 'Bottom' ? '#ef4444' : '#64748b'} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};
