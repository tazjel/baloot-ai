import React, { useEffect, useRef } from 'react';
import { Trophy, RefreshCw, Home, Eye } from 'lucide-react';

interface VictoryModalProps {
    scores: { us: number; them: number };
    onRematch: () => void;
    onHome: () => void;
    onReview?: () => void;
}

const VictoryModal: React.FC<VictoryModalProps> = ({ scores, onRematch, onHome, onReview }) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const isWin = scores.us >= scores.them;

    useEffect(() => {
        if (!isWin) return;

        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        const particles: any[] = [];
        const colors = ['#f00', '#0f0', '#00f', '#ff0', '#0ff', '#f0f'];

        for (let i = 0; i < 200; i++) {
            particles.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height - canvas.height,
                vx: Math.random() * 4 - 2,
                vy: Math.random() * 4 + 2,
                color: colors[Math.floor(Math.random() * colors.length)],
                size: Math.random() * 5 + 2
            });
        }

        const animate = () => {
            if (!ctx) return;
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            particles.forEach(p => {
                p.x += p.vx;
                p.y += p.vy;
                if (p.y > canvas.height) p.y = -10;

                ctx.fillStyle = p.color;
                ctx.fillRect(p.x, p.y, p.size, p.size);
            });

            requestAnimationFrame(animate);
        };

        const animId = requestAnimationFrame(animate);
        return () => cancelAnimationFrame(animId);

    }, [isWin]);

    return (
        <div className="absolute inset-0 z-[300] flex items-center justify-center bg-black/95 backdrop-blur-xl animate-in fade-in duration-1000">
            {isWin && <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none" />}

            <div className="relative z-10 text-center flex flex-col items-center">
                <div className={`
                    w-32 h-32 rounded-full flex items-center justify-center mb-6 shadow-[0_0_50px_currentColor]
                    ${isWin ? 'bg-yellow-500/20 text-yellow-500' : 'bg-gray-500/20 text-gray-500'}
                `}>
                    <Trophy size={64} />
                </div>

                <h1 className={`text-6xl font-black mb-2 tracking-tighter uppercase ${isWin ? 'text-yellow-500' : 'text-gray-400'}`}>
                    {isWin ? 'Victory!' : 'Defeat'}
                </h1>

                <p className="text-2xl text-gray-400 mb-8 font-serif tracking-widest">
                    {isWin ? 'The Championship is Yours' : 'Better Luck Next Time'}
                </p>

                <div className="flex items-center gap-12 mb-12 bg-white/5 p-8 rounded-2xl border border-white/10">
                    <div className="text-center">
                        <div className="text-sm text-gray-500 uppercase tracking-widest mb-2">Us</div>
                        <div className={`text-5xl font-bold ${isWin ? 'text-green-500' : 'text-white'}`}>{scores.us}</div>
                    </div>
                    <div className="text-2xl text-gray-600 font-light">vs</div>
                    <div className="text-center">
                        <div className="text-sm text-gray-500 uppercase tracking-widest mb-2">Them</div>
                        <div className={`text-5xl font-bold ${!isWin ? 'text-red-500' : 'text-white'}`}>{scores.them}</div>
                    </div>
                </div>

                <div className="flex gap-4">
                    <button onClick={onHome} className="px-8 py-4 rounded-xl bg-gray-800 hover:bg-gray-700 text-white font-bold flex items-center gap-2 transition-all">
                        <Home size={20} />
                        <span>Main Menu</span>
                    </button>
                    {onReview && (
                        <button onClick={onReview} className="px-8 py-4 rounded-xl bg-gray-600 hover:bg-gray-500 text-white font-bold flex items-center gap-2 transition-all">
                            <Eye size={20} />
                            <span>Review</span>
                        </button>
                    )}
                    <button onClick={onRematch} className="px-8 py-4 rounded-xl bg-white text-black hover:bg-gray-200 font-bold flex items-center gap-2 shadow-[0_0_30px_rgba(255,255,255,0.3)] transition-all">
                        <RefreshCw size={20} />
                        <span>Play Again</span>
                    </button>
                </div>
            </div>
        </div>
    );
};

export default VictoryModal;
