import React, { useRef, useEffect } from 'react';
import { Settings, HelpCircle, LogOut, Volume2, MessageSquare, Signal, Users, User, Trophy, History, Crown, Coins, Star } from 'lucide-react';
import ScoreSheet from './ScoreSheet';
import { UserProfile, RoundResult, Player } from '../types';

interface SidebarProps {
  scores: { us: number; them: number }; // Round Scores
  matchScores: { us: number; them: number }; // Global Scores (Target 152)
  roundHistory: RoundResult[];
  userProfile?: UserProfile;
  messages: { sender: string, text: string }[];
  roomId?: string | null;
  players?: Player[]; // Added players for Bot Insights
}

const Sidebar: React.FC<SidebarProps> = ({ scores, matchScores, roundHistory, userProfile, messages, roomId, players }) => {
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="hidden md:flex flex-col w-72 bg-white/80 backdrop-blur-lg border-r border-white/30 h-full text-gray-800 shrink-0 z-30 shadow-lg">

      {/* --- Top Icons --- */}
      <div className="flex justify-between px-4 py-3 bg-white/50 border-b border-gray-200/50">
        <button className="text-gray-500 hover:text-red-500 transition-colors" aria-label="Log out"><LogOut size={20} /></button>
        <button className="text-gray-500 hover:text-blue-500 transition-colors" aria-label="Help"><HelpCircle size={20} /></button>
        <button className="text-gray-500 hover:text-gray-800 transition-colors" aria-label="Settings"><Settings size={20} /></button>
        <button className="text-gray-500 hover:text-gray-800 transition-colors" aria-label="Toggle sound"><Volume2 size={20} /></button>
      </div>

      {/* --- Session Info --- */}
      <div className="p-4 bg-white/40 border-b border-gray-200/50">
        <div className="flex justify-between items-center mb-1">
          <span className="text-gray-500 text-xs font-tajawal">رقم الجلسة</span>
          <div className="flex flex-col items-end">
            {userProfile ? (
              <>
                <span className="text-xs font-bold text-amber-600">Lvl {userProfile.level}</span>
                <span className="text-[10px] text-gray-400">{userProfile.coins} Coins</span>
              </>
            ) : (
              <span className="text-xs text-gray-400">Guest</span>
            )}
          </div>
        </div>
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-bold tracking-wider text-gray-800">{roomId || "OFFLINE"}</h2>
          <Signal size={16} className={roomId ? "text-green-500" : "text-gray-400"} />
        </div>
      </div>

      {/* --- Score Board (Qayd) --- */}
      <div className="p-4">
        <ScoreSheet
          roundHistory={roundHistory}
          matchScores={matchScores}
          currentRoundScore={scores}
        />
      </div>

      {/* --- Spectators --- */}
      <div className="px-4 py-2 border-b border-gray-200/50">
        <div className="flex items-center gap-2 text-gray-500">
          <Users size={14} />
          <span className="text-xs font-bold">المشاهدون (0)</span>
        </div>
      </div>

      {/* --- Bot Insights REMOVED (Moved to dedicated Left Panel) --- */}

      {/* --- Chat Area --- */}
      <div className="flex-1 flex flex-col min-h-0 bg-white/30">
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {messages.length === 0 && (
            <div className="text-center text-gray-400 text-xs mt-4 italic">لا توجد رسائل</div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className="text-sm">
              <span className="text-amber-600 font-bold ml-1">{msg.sender}:</span>
              <span className="text-gray-700">{msg.text}</span>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        <div className="p-3 bg-white/50 border-t border-gray-200/50 flex items-center gap-2">
          <input
            type="text"
            placeholder="رسالتك..."
            className="flex-1 bg-white/70 border border-gray-200 rounded-full px-4 py-2 text-gray-800 text-right text-sm placeholder-gray-400 focus:outline-none focus:border-amber-400 transition-colors"
          />
          <button className="p-2 bg-amber-500 hover:bg-amber-400 rounded-full text-white transition-colors shadow-md" aria-label="Send message">
            <MessageSquare size={16} />
          </button>
        </div>
      </div>

    </div>
  );
};

export default Sidebar;