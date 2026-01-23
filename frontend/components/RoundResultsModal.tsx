import React, { useEffect } from 'react';
import { RoundResult } from '../types';
import { ArrowLeft } from 'lucide-react';
import confetti from 'canvas-confetti';

interface RoundResultsModalProps {
    result: RoundResult | null;
    bidderTeam: 'us' | 'them' | null;
    bidType: 'SUN' | 'HOKUM' | 'ASHKAL' | null;
    onClose: () => void;
    isOpen: boolean;
    onReview?: () => void;
}

const RoundResultsModal: React.FC<RoundResultsModalProps> = ({ result, bidderTeam, bidType, onClose, isOpen, onReview }) => {

    // Play confetti only on open if US won
    useEffect(() => {
        if (isOpen && result && result.winner === 'us') {
            const duration = 2000;
            const end = Date.now() + duration;
            (function frame() {
                confetti({
                    particleCount: 5, angle: 60, spread: 55, origin: { x: 0 },
                    colors: ['#4ade80', '#22c55e', '#fbbf24']
                });
                confetti({
                    particleCount: 5, angle: 120, spread: 55, origin: { x: 1 },
                    colors: ['#4ade80', '#22c55e', '#fbbf24']
                });
                if (Date.now() < end) requestAnimationFrame(frame);
            }());
        }
    }, [isOpen, result]);

    if (!isOpen || !result) return null;

    const usWon = result.winner === 'us';
    const isBidderWinner = bidderTeam === result.winner;

    // Arabic Translations
    const bidTypeMap: Record<string, string> = { 'SUN': 'صن', 'HOKUM': 'حكم', 'ASHKAL': 'أشكال' };
    const bidLabel = bidType ? bidTypeMap[bidType] || bidType : '-';

    const bidderLabel = bidderTeam === 'us' ? 'فريقنا' : bidderTeam === 'them' ? 'فريقهم' : '-';
    const stateLabel = isBidderWinner ? 'ربحانة' : 'خسرانة';
    const stateColor = isBidderWinner ? 'text-green-600' : 'text-red-600';

    // Helper to format projects for display
    // Example: "20 سرا"
    const formatProjects = (projects: any[]) => {
        if (!projects || projects.length === 0) return null;
        return projects.map((p, idx) => {
            let name = p.type;
            if (p.type === 'SIRA') name = 'سرا';
            if (p.type === 'FIFTY') name = 'خمسين';
            if (p.type === 'HUNDRED') name = 'مية';
            if (p.type === 'FOUR_HUNDRED') name = 'أربعمية';
            if (p.type === 'BALOOT') name = 'بلوت';

            // Points usually: Score (e.g. 20) + Name
            // But if HOKUM, score is divided?
            // Usually display RAW decl score (e.g. 20) not game points (2).
            const score = p.score || 0;
            return <div key={idx} className="text-xs font-bold text-slate-700">{score} {name}</div>
        });
    };

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 font-tajawal" dir="rtl">
            {/* Main Card Container - Simulating the beige/paper look */}
            <div className="relative w-full max-w-lg bg-[#e8e4dc] rounded-xl shadow-2xl overflow-hidden border-4 border-[#8c7b6b]">

                {/* Header Section (White Box) */}
                <div className="bg-white/80 p-6 m-4 rounded-lg shadow-sm border border-stone-200">
                    <div className="flex justify-between items-center mb-2">
                        <div className="text-stone-500 font-bold">اللعبة: <span className="text-black">{bidLabel}</span></div>
                        <div className="text-stone-500 font-bold">المشتري أو البديل: <span className="text-black">{bidderLabel}</span></div>
                    </div>
                    <div className="text-center mt-2">
                        <span className="text-stone-500 font-bold">نتيجة الشراء: </span>
                        <span className={`font-black text-xl ${stateColor}`}>{stateLabel}</span>
                    </div>
                </div>

                {/* "Nashra" (Bulletin) Section */}
                <div className="relative mx-4 mb-4 bg-[#dcdcdc] rounded-lg overflow-hidden border border-stone-300">

                    {/* The "Nashra" Tab on the Right */}
                    <div className="absolute top-0 right-0 bg-[#8b5a2b] text-white py-1 px-6 rounded-bl-xl font-bold text-lg shadow-md z-10">
                        النـشـرة
                    </div>

                    {/* Table Header */}
                    <div className="flex pt-10 pb-2 border-b border-stone-300 bg-[#e0e0e0]">
                        <div className="w-1/3 text-center font-bold text-stone-700">لنا</div>
                        <div className="w-1/3 text-center font-bold text-stone-700">لهم</div>
                        <div className="w-1/3"></div> {/* Label Column is visually on the RIGHT in RTL, but DOM order... RTL: Right is first? 
                             Tailwind RTL: 
                             Flex row in RTL: 1st child is Right.
                             So "Label" column should be FIRST child?
                             Use explicit order or standard flow. 
                             Standard flow RTL: 
                             [Start] -> [End]
                             Visual: [Right] -> [Left]
                             Image: Labels are on the RIGHT (Start in RTL).
                             So Labels should be FIRST div.
                        */}
                    </div>

                    {/* Table Body */}
                    <div className="flex flex-col text-lg">
                        {/* Aklat Row */}
                        <div className="flex items-center py-2 border-b border-stone-300/50">
                            <div className="w-1/4 text-center font-bold text-stone-800 bg-[#8b5a2b] text-white mx-2 rounded shadow-sm text-sm py-1">الأكلات</div>
                            <div className="flex-1 flex text-center font-mono font-bold text-black text-xl">
                                <div className="w-1/2">{result.us.aklat}</div>
                                <div className="w-1/2">{result.them.aklat}</div>
                            </div>
                        </div>

                        {/* Ardh (Floor/Last) Row */}
                        <div className="flex items-center py-2 border-b border-stone-300/50">
                            <div className="w-1/4 text-center font-bold text-stone-600 text-sm">الأرض</div>
                            <div className="flex-1 flex text-center font-mono font-bold text-slate-800">
                                <div className="w-1/2">{result.us.ardh || ''}</div>
                                <div className="w-1/2">{result.them.ardh || ''}</div>
                            </div>
                        </div>

                        {/* Projects Row */}
                        <div className="flex items-center py-2 border-b border-stone-300/50 min-h-[50px]">
                            <div className="w-1/4 text-center font-bold text-stone-600 text-sm">المشاريع</div>
                            <div className="flex-1 flex text-center">
                                <div className="w-1/2 flex flex-col items-center justify-center">
                                    {formatProjects(result.us.projects)}
                                </div>
                                <div className="w-1/2 flex flex-col items-center justify-center">
                                    {formatProjects(result.them.projects)}
                                </div>
                            </div>
                        </div>

                        {/* Abnat Row (Total Raw) */}
                        <div className="flex items-center py-3 border-b border-stone-300/50 bg-black/5">
                            <div className="w-1/4 text-center font-bold text-stone-700 text-sm">الابناط</div>
                            <div className="flex-1 flex text-center font-mono font-black text-2xl text-stone-800">
                                <div className="w-1/2">{result.us.abnat}</div>
                                <div className="w-1/2">{result.them.abnat}</div>
                            </div>
                        </div>

                        {/* Result Row (Highlighted) */}
                        <div className="flex items-center py-4 bg-[#e8e4dc]">
                            <div className="w-1/4 text-center font-bold text-white bg-[#d94a4a] mx-2 rounded py-2 shadow-md">النتيجة</div>
                            <div className="flex-1 flex text-center font-mono font-black text-4xl text-black">
                                <div className="w-1/2">{result.us.result}</div>
                                <div className="w-1/2">{result.them.result}</div>
                            </div>
                        </div>

                    </div>
                </div>

                {/* Footer Buttons */}
                <div className="mt-6 mb-4 px-4 flex gap-3">
                    <button
                        onClick={onClose}
                        className="w-full bg-[#a89f91] hover:bg-[#968c7d] text-white font-bold py-3 rounded-lg shadow-lg active:scale-95 transition-all text-xl"
                    >
                        عـــودة
                    </button>
                    {onReview && (
                        <button
                            onClick={onReview}
                            className="w-1/3 bg-[#546e7a] hover:bg-[#455a64] text-white font-bold py-3 rounded-lg shadow-lg active:scale-95 transition-all text-sm"
                        >
                            مراجعة
                        </button>
                    )}
                </div>

            </div>
        </div>
    );
};

export default RoundResultsModal;
