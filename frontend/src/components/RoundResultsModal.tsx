import React, { useEffect } from 'react';
import { RoundResult, DeclaredProject } from '../types';
import { ArrowLeft } from 'lucide-react';
import confetti from 'canvas-confetti';
import { soundManager } from '../services/SoundManager';

interface RoundResultsModalProps {
    result: RoundResult | null;
    bidderTeam: 'us' | 'them' | null;
    bidType: 'SUN' | 'HOKUM' | 'ASHKAL' | null;
    onClose: () => void;
    isOpen: boolean;
    onReview?: () => void;
}

const RoundResultsModal: React.FC<RoundResultsModalProps> = ({ result, bidderTeam, bidType, onClose, isOpen, onReview }) => {

    // Play confetti + jingles on open
    useEffect(() => {
        if (!isOpen || !result) return;

        // Detect Kaboot for sound
        const isKabootResult = (result.us.aklat === 0 || result.them.aklat === 0) && (result.us.aklat + result.them.aklat > 0);

        if (result.winner === 'us') {
            // Victory confetti
            const duration = isKabootResult ? 3000 : 2000;
            const end = Date.now() + duration;
            const particleCount = isKabootResult ? 8 : 5;
            (function frame() {
                confetti({
                    particleCount, angle: 60, spread: 55, origin: { x: 0 },
                    colors: isKabootResult ? ['#FFD700', '#FFA500', '#FF4500', '#D4AF37'] : ['#4ade80', '#22c55e', '#fbbf24']
                });
                confetti({
                    particleCount, angle: 120, spread: 55, origin: { x: 1 },
                    colors: isKabootResult ? ['#FFD700', '#FFA500', '#FF4500', '#D4AF37'] : ['#4ade80', '#22c55e', '#fbbf24']
                });
                if (Date.now() < end) requestAnimationFrame(frame);
            }());

            // M18: Sound
            if (isKabootResult) {
                soundManager.playKabootSound();
            } else {
                soundManager.playVictoryJingle();
            }
        } else if (result.winner === 'them') {
            // M18: Defeat jingle
            if (isKabootResult) {
                soundManager.playKabootSound(); // Kaboot is dramatic regardless
            } else {
                soundManager.playDefeatJingle();
            }
        }
    }, [isOpen, result]);

    // Auto-close after 2 seconds
    useEffect(() => {
        if (isOpen) {
            const timer = setTimeout(() => {
                onClose();
            }, 2000);
            return () => clearTimeout(timer);
        }
    }, [isOpen, onClose]);

    if (!isOpen || !result) return null;

    const usWon = result.winner === 'us';
    const isBidderWinner = bidderTeam === result.winner;

    // Arabic Translations
    const bidTypeMap: Record<string, string> = { 'SUN': 'صن', 'HOKUM': 'حكم', 'ASHKAL': 'أشكال' };
    const bidLabel = bidType ? bidTypeMap[bidType] || bidType : '-';


    const bidderLabel = bidderTeam === 'us' ? 'فريقنا' : bidderTeam === 'them' ? 'فريقهم' : '-';

    // Detect Kaboot (one team got 0 tricks)
    const isKaboot = (result.us.aklat === 0 || result.them.aklat === 0) && (result.us.aklat + result.them.aklat > 0);
    const kabootWinner = result.us.aklat === 0 ? 'them' : 'us';

    // Custom label for Qayd/Violation
    let stateLabel = isBidderWinner ? 'ربحانة' : 'خسرانة';
    if (result.reason && result.reason.includes('QAYD')) {
        stateLabel = 'صحة القيد'; // Valid Qayd
    }

    const stateColor = (result.reason && result.reason.includes('QAYD'))
        ? 'text-amber-600'
        : (isBidderWinner ? 'text-green-600' : 'text-red-600');

    // Helper to format projects for display
    // Example: "20 سرا"
    const PROJECT_NAMES: Record<string, string> = {
        'SIRA': 'سرا',
        'FIFTY': 'خمسين',
        'HUNDRED': 'مية',
        'FOUR_HUNDRED': 'أربعمية',
        'BALOOT': 'بلوت',
    };

    const formatProjects = (projects: DeclaredProject[]) => {
        if (!projects || projects.length === 0) return null;
        return projects.map((p, idx) => {
            const name = PROJECT_NAMES[p.type] || p.type;
            const score = p.score || 0;
            return <div key={idx} className="text-xs font-bold text-slate-700">{score} {name}</div>
        });
    };

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 font-tajawal" dir="rtl" role="dialog" aria-modal="true" aria-label="Round results">
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

                {/* Kaboot (Galoss) Banner */}
                {isKaboot && (
                    <div className="mx-4 mb-2 bg-gradient-to-r from-rose-600 to-red-700 text-white p-3 rounded-lg shadow-lg border border-rose-400 text-center animate-kaboot-burst">
                        <div className="text-2xl font-black mb-0.5">كبوت! 🏆</div>
                        <div className="text-sm opacity-90">
                            {kabootWinner === 'us' ? 'فريقنا أخذ جميع الأكلات' : 'فريقهم أخذ جميع الأكلات'}
                        </div>
                    </div>
                )}

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

            </div>
        </div>
    );
};

export default RoundResultsModal;
