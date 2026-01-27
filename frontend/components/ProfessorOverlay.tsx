import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ProfessorOverlayProps {
    intervention: {
        message: string;
        better_card: any;
        reason: string;
    } | null;
    onUndo: () => void;
    onContinue: () => void;
}

export const ProfessorOverlay: React.FC<ProfessorOverlayProps> = ({ intervention, onUndo, onContinue }) => {
    if (!intervention) return null;

    return (
        <div className="fixed inset-0 z-[200] bg-black/70 flex items-center justify-center p-4">
            <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="bg-slate-800 rounded-2xl p-8 max-w-lg w-full border-2 border-yellow-500 shadow-2xl relative overflow-hidden"
                dir="rtl"
            >
                {/* Background decorative elements */}
                <div className="absolute top-0 left-0 w-full h-2 bg-yellow-500" />

                <div className="flex flex-col items-center text-center gap-4">
                    <div className="text-6xl mb-2">🧑‍🏫</div>

                    <h2 className="text-2xl font-bold text-yellow-400">لحظة من فضلك!</h2>

                    <p className="text-white text-lg leading-relaxed">
                        {intervention.message}
                    </p>

                    {intervention.reason && (
                        <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700 w-full text-slate-300 text-sm mt-2">
                            💡 {intervention.reason}
                        </div>
                    )}

                    <div className="flex gap-4 mt-6 w-full">
                        <button
                            onClick={onUndo}
                            className="flex-1 bg-yellow-600 hover:bg-yellow-500 text-white font-bold py-3 px-6 rounded-xl transition-all shadow-lg hover:shadow-yellow-500/20"
                        >
                            حاول مرة أخرى
                        </button>

                        <button
                            onClick={onContinue}
                            className="flex-1 bg-slate-700 hover:bg-slate-600 text-slate-300 font-semibold py-3 px-6 rounded-xl transition-all"
                        >
                            أعرف ماذا أفعل
                        </button>
                    </div>
                </div>
            </motion.div>
        </div>
    );
}
