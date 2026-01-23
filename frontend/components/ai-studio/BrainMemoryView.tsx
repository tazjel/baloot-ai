import { Brain, RefreshCw, X, ArrowLeft, Code, Database } from 'lucide-react';
import { getBrainMemory, deleteBrainMemory } from '../../services/trainingService';

interface BrainMemoryViewProps {
    onBack: () => void;
}

const BrainMemoryView: React.FC<BrainMemoryViewProps> = ({ onBack }) => {
    const [brainMemory, setBrainMemory] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [showJson, setShowJson] = useState(false);

    useEffect(() => {
        loadBrainMemory();
    }, []);

    const loadBrainMemory = async () => {
        setLoading(true);
        const res = await getBrainMemory();
        if (res.memory) {
            setBrainMemory(res.memory);
        }
        setLoading(false);
    };

    const handleDeleteMemory = async (hash: string) => {
        if (!confirm("Forget this move?")) return;
        await deleteBrainMemory(hash);
        loadBrainMemory();
    };

    const getSuitSymbol = (suit: string) => {
        const symbols: Record<string, string> = { S: '♠', H: '♥', D: '♦', C: '♣' };
        return symbols[suit] || suit;
    };

    return (
        <div className="flex flex-col h-full w-full bg-slate-900 text-white font-tajawal p-6 overflow-hidden">
            <div className="flex items-center justify-between mb-6 shrink-0">
                <div className="flex items-center gap-4">
                    <button onClick={onBack} className="p-2 bg-slate-800 rounded-full hover:bg-slate-700">
                        <ArrowLeft size={24} />
                    </button>
                    <div>
                        <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-500 to-purple-600 bg-clip-text text-transparent flex items-center gap-2">
                            <Brain /> ذاكرة البوت
                        </h1>
                        <p className="text-slate-400">الحركات التي تعلمها البوت من التصحيحات السابقة</p>
                    </div>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => setShowJson(!showJson)}
                        className={`flex items-center gap-2 px-3 py-2 rounded border transition-colors ${showJson ? 'bg-indigo-600 border-indigo-400 text-white' : 'bg-slate-800 border-slate-600 text-slate-400 hover:text-white'}`}
                        title="Show Raw Data"
                    >
                        <Code size={18} />
                        <span className="hidden sm:inline">{showJson ? 'إخفاء البيانات' : 'عرض البيانات'}</span>
                    </button>
                    <button onClick={loadBrainMemory} className="p-2 bg-slate-800 rounded hover:bg-slate-700 border border-slate-600">
                        <RefreshCw size={20} className={loading ? "animate-spin" : ""} />
                    </button>
                </div>
            </div>

            <div className="flex-1 overflow-auto bg-slate-800/30 rounded-xl border border-slate-700 p-6">
                {brainMemory.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-slate-500">
                        <Brain size={64} className="mb-4 opacity-50" />
                        <p className="text-xl">لا توجد حركات محفوظة في الذاكرة</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {brainMemory.map((mem) => (
                            <div key={mem.hash} className="bg-slate-800 p-5 rounded-xl border border-slate-600 shadow-lg group hover:border-indigo-500 transition-colors relative flex flex-col">
                                <div className="flex justify-between items-start mb-3">
                                    <div className="bg-slate-900 px-2 py-1 rounded text-xs font-mono text-slate-500 select-all border border-slate-700 flex items-center gap-1">
                                        <Database size={12} />
                                        {mem.hash.substring(0, 12)}...
                                    </div>
                                    <button
                                        onClick={() => handleDeleteMemory(mem.hash)}
                                        className="text-slate-600 hover:text-red-400 hover:bg-red-900/20 p-1.5 rounded transition-colors opacity-0 group-hover:opacity-100"
                                        title="Delete Memory"
                                    >
                                        <X size={16} />
                                    </button>
                                </div>

                                {showJson ? (
                                    <div className="flex-1 bg-slate-950 p-3 rounded-lg border border-slate-700 font-mono text-[10px] text-indigo-300 overflow-auto max-h-48">
                                        <pre>{JSON.stringify(mem.data, null, 2)}</pre>
                                    </div>
                                ) : (
                                    <>
                                        <div className="mb-4">
                                            <div className="text-xs text-slate-400 mb-1 uppercase tracking-wider font-bold">Learned Action</div>
                                            <div className="flex items-center gap-2">
                                                <span className={`px-3 py-1 rounded text-sm font-bold border ${mem.data.action === 'PASS' ? 'bg-slate-700 border-slate-500 text-white' : 'bg-green-900/50 border-green-500 text-green-300'}`}>
                                                    {mem.data.action}
                                                </span>
                                                {mem.data.card && (
                                                    <span className={`px-3 py-1 rounded text-sm font-bold bg-white text-black border border-slate-300 flex items-center gap-1 ${['H', 'D'].includes(mem.data.card.suit) ? 'text-red-600' : ''}`}>
                                                        {mem.data.card.rank}<span>{getSuitSymbol(mem.data.card.suit)}</span>
                                                    </span>
                                                )}
                                                {mem.data.suit && (
                                                    <span className={`text-2xl ${['H', 'D'].includes(mem.data.suit) ? 'text-red-500' : 'text-slate-200'}`}>
                                                        {getSuitSymbol(mem.data.suit)}
                                                    </span>
                                                )}
                                            </div>
                                        </div>

                                        <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-700/50 flex-1">
                                            <div className="text-xs text-slate-500 mb-1 flex items-center gap-1"><Brain size={12} /> Reasoning</div>
                                            <p className="text-sm text-slate-300 italic">
                                                "{mem.data.reason || 'No reasoning stored'}"
                                            </p>
                                        </div>
                                    </>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default BrainMemoryView;
