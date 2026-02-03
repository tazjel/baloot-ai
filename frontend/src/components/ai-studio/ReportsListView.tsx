import React, { useState } from 'react';
import { RefreshCw, CheckCircle, Layers } from 'lucide-react';

interface ReportsListViewProps {
    examples: any[];
    loading: boolean;
    onLoadData: () => void;
    onDuplicate: (example: any) => void;
}

const ReportsListView: React.FC<ReportsListViewProps> = ({ examples, loading, onLoadData, onDuplicate }) => {
    const [selectedExample, setSelectedExample] = useState<any>(null);

    return (
        <div className="flex flex-col lg:flex-row flex-1 gap-6 overflow-hidden overflow-y-auto lg:overflow-y-hidden">
            {/* List */}
            <div className="w-full lg:w-1/3 bg-slate-800 rounded-xl p-4 overflow-y-auto border border-slate-700 order-2 lg:order-1">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold text-slate-300">سجل التصحيحات ({examples.length})</h2>
                    <button onClick={onLoadData} className="p-2 bg-slate-700 rounded hover:bg-slate-600"><RefreshCw size={16} /></button>
                </div>
                <div className="flex flex-col gap-3">
                    {loading ? <p>جاري التحميل...</p> : examples.map((ex, idx) => (
                        <div
                            key={idx}
                            onClick={() => setSelectedExample(ex)}
                            className={`p-4 rounded-lg cursor-pointer transition-all border ${selectedExample === ex ? 'bg-slate-700 border-yellow-500' : 'bg-slate-900/50 border-slate-700 hover:bg-slate-700'}`}
                        >
                            <div className="flex justify-between mb-2">
                                <span className="text-xs text-slate-500">{new Date(ex.created_on).toLocaleString()}</span>
                                <span className="text-xs px-2 py-0.5 bg-blue-900 text-blue-200 rounded-full">
                                    {ex.contextHash?.startsWith('scen-') ? 'Scenario' : 'Report'}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <div className="text-green-400 font-bold">{JSON.parse(ex.correct_move_json || '"{}"').action || ex.correct_move_json}</div>
                            </div>
                            <div className="text-xs text-slate-400 mt-2 truncate">{ex.reason}</div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Detail View */}
            <div className="flex-1 bg-slate-800 rounded-xl p-6 border border-slate-700 flex flex-col items-center justify-center overflow-auto order-1 lg:order-2">
                {selectedExample ? (
                    <div className="w-full max-w-2xl">
                        <h2 className="text-2xl font-bold mb-6 text-center border-b border-slate-700 pb-4">تفاصيل الحالة</h2>

                        <div className="grid grid-cols-2 gap-8 mb-8">
                            <div className="bg-red-900/20 p-6 rounded-xl border border-red-900/50 text-center">
                                <div className="text-red-400 text-sm mb-2">قرار البوت</div>
                                <div className="text-xl font-bold text-red-200 truncate">{selectedExample.bad_move_json}</div>
                            </div>
                            <div className="bg-green-900/20 p-6 rounded-xl border border-green-900/50 text-center">
                                <div className="text-green-400 text-sm mb-2">الحل الصحيح</div>
                                <div className="text-xl font-bold text-green-200 truncate">{selectedExample.correct_move_json}</div>
                            </div>
                        </div>

                        <div className="bg-slate-900 p-6 rounded-xl mb-6">
                            <h3 className="text-sm text-slate-400 mb-2">السبب / الشرح</h3>
                            <p className="text-lg leading-relaxed">{selectedExample.reason}</p>
                        </div>

                        {selectedExample.contextHash?.startsWith('scen-') && (
                            <div className="bg-blue-900/20 border border-blue-500/30 p-4 rounded-lg text-center text-blue-300 mb-4 bg-red">
                                <div className="mb-2">ℹ️ This is a manually created scenario.</div>
                                <button
                                    onClick={() => onDuplicate(selectedExample)}
                                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded font-bold flex items-center gap-2 mx-auto"
                                >
                                    <Layers size={16} /> Edit / Duplicate
                                </button>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="text-center text-slate-500">
                        <CheckCircle size={64} className="mx-auto mb-4 opacity-20" />
                        <p className="text-xl">اختر حالة لعرض التفاصيل</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ReportsListView;
