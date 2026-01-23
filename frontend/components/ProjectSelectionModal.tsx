import React from 'react';
import { X, Trophy, Crown, Layers, Star } from 'lucide-react';

interface ProjectSelectionModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSelect: (projectType: string) => void;
}

const ProjectSelectionModal: React.FC<ProjectSelectionModalProps> = ({ isOpen, onClose, onSelect }) => {
    if (!isOpen) return null;

    const projects = [
        { id: 'SIRA', label: 'سرا', icon: <Layers size={24} />, desc: '3 consecutive' },
        { id: 'FIFTY', label: 'خمسين', icon: <Star size={24} />, desc: '4 consecutive' },
        { id: 'HUNDRED', label: 'مية', icon: <Trophy size={24} />, desc: '5 consecutive / 4 Aces' },
        { id: 'FOUR_HUNDRED', label: 'أربعمية', icon: <Crown size={24} />, desc: '4 Aces (Sun)' },
        { id: 'BALOOT', label: 'بلوت', icon: <Crown size={24} />, desc: 'K + Q (Hokum)' },
    ];

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
            <div className="relative bg-gradient-to-b from-gray-900 to-gray-800 border-2 border-yellow-600 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden transform transition-all scale-100">

                {/* Header */}
                <div className="bg-gradient-to-r from-yellow-700/20 to-yellow-900/20 p-4 border-b border-yellow-600/30 flex justify-between items-center">
                    <h2 className="text-xl font-black text-yellow-500 flex items-center gap-2">
                        <Trophy className="text-yellow-400" />
                        يعلن مشاريع
                    </h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                        <X size={24} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 grid grid-cols-2 gap-4">
                    {projects.map((p) => (
                        <button
                            key={p.id}
                            onClick={() => onSelect(p.id)}
                            className="group relative flex flex-col items-center justify-center p-4 bg-gray-800/50 hover:bg-yellow-900/20 border border-gray-600 hover:border-yellow-500 rounded-xl transition-all duration-300 hover:shadow-[0_0_15px_rgba(234,179,8,0.2)]"
                        >
                            <div className="mb-3 p-3 bg-gray-700/50 group-hover:bg-yellow-500/20 rounded-full transition-colors text-yellow-500">
                                {p.icon}
                            </div>
                            <span className="text-lg font-bold text-gray-200 group-hover:text-yellow-400 mb-1">{p.label}</span>
                            <span className="text-xs text-gray-500 group-hover:text-yellow-200/60 uppercase tracking-widest">{p.desc}</span>
                        </button>
                    ))}
                </div>

                {/* Footer */}
                <div className="bg-gray-900/50 p-4 text-center">
                    <p className="text-xs text-gray-500">
                        Select a project to verify its validity.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default ProjectSelectionModal;
