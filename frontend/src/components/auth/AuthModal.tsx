import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { X, Mail, Lock, User, UserPlus, LogIn, Loader } from 'lucide-react';

interface AuthModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose }) => {
    const { login, register, isLoading } = useAuth();
    const [mode, setMode] = useState<'LOGIN' | 'REGISTER'>('LOGIN');
    const [error, setError] = useState<string | null>(null);

    // Form State
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (mode === 'LOGIN') {
            const err = await login(email, password);
            if (!err) onClose();
            else setError(err);
        } else {
            const err = await register(firstName, lastName, email, password);
            if (!err) {
                // Success! Switch to Login
                setMode('LOGIN');
                setError("Registration successful! Please login.");
            } else {
                setError(err);
            }
        }
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 font-tajawal">
            <div className="relative w-full max-w-md bg-[#1e1e1e] border border-gray-700 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">

                {/* Close Button */}
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 p-2 text-gray-400 hover:text-white rounded-full hover:bg-white/10 transition-colors"
                >
                    <X size={20} />
                </button>

                {/* Header */}
                <div className="bg-gradient-to-r from-yellow-900/20 to-transparent p-6 border-b border-gray-700">
                    <h2 className="text-2xl font-bold text-yellow-500 flex items-center gap-2">
                        {mode === 'LOGIN' ? <LogIn size={24} /> : <UserPlus size={24} />}
                        {mode === 'LOGIN' ? 'تسجيل الدخول' : 'إنشاء حساب جديد'}
                    </h2>
                    <p className="text-gray-400 text-sm mt-1">
                        {mode === 'LOGIN' ? 'مرحباً بعودتك إلى بلوت!' : 'انضم إلينا وابدأ اللعب!'}
                    </p>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6 space-y-4" dir="rtl">
                    {error && (
                        <div className={`p-3 rounded-lg text-sm text-center ${error.includes('success') ? 'bg-green-900/30 text-green-400 border border-green-500/30' : 'bg-red-900/30 text-red-400 border border-red-500/30'}`}>
                            {error}
                        </div>
                    )}

                    {mode === 'REGISTER' && (
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1">
                                <label className="text-xs text-gray-400">الاسم الأول</label>
                                <div className="relative">
                                    <User className="absolute right-3 top-3 text-gray-500" size={16} />
                                    <input
                                        type="text"
                                        value={firstName}
                                        onChange={e => setFirstName(e.target.value)}
                                        className="w-full bg-[#121212] border border-gray-600 rounded-lg py-2.5 pr-10 pl-3 text-white focus:border-yellow-500 focus:outline-none text-sm"
                                        placeholder="الاسم"
                                        required
                                    />
                                </div>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs text-gray-400">اسم العائلة</label>
                                <input
                                    type="text"
                                    value={lastName}
                                    onChange={e => setLastName(e.target.value)}
                                    className="w-full bg-[#121212] border border-gray-600 rounded-lg py-2.5 px-3 text-white focus:border-yellow-500 focus:outline-none text-sm"
                                    placeholder="العائلة"
                                    required
                                />
                            </div>
                        </div>
                    )}

                    <div className="space-y-1">
                        <label className="text-xs text-gray-400">البريد الإلكتروني</label>
                        <div className="relative">
                            <Mail className="absolute right-3 top-3 text-gray-500" size={16} />
                            <input
                                type="email"
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                className="w-full bg-[#121212] border border-gray-600 rounded-lg py-2.5 pr-10 pl-3 text-white focus:border-yellow-500 focus:outline-none text-sm ltr"
                                placeholder="example@email.com"
                                style={{ direction: 'ltr', textAlign: 'right' }}
                                required
                            />
                        </div>
                    </div>

                    <div className="space-y-1">
                        <label className="text-xs text-gray-400">كلمة المرور</label>
                        <div className="relative">
                            <Lock className="absolute right-3 top-3 text-gray-500" size={16} />
                            <input
                                type="password"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                className="w-full bg-[#121212] border border-gray-600 rounded-lg py-2.5 pr-10 pl-3 text-white focus:border-yellow-500 focus:outline-none text-sm"
                                placeholder="••••••••"
                                required
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full bg-yellow-600 hover:bg-yellow-500 text-black font-bold py-3 rounded-lg transition-all mt-6 flex items-center justify-center gap-2"
                    >
                        {isLoading ? <Loader className="animate-spin" size={20} /> : (mode === 'LOGIN' ? 'دخول' : 'تسجيل')}
                    </button>

                    <div className="text-center pt-2">
                        <button
                            type="button"
                            onClick={() => { setError(null); setMode(mode === 'LOGIN' ? 'REGISTER' : 'LOGIN'); }}
                            className="text-gray-400 hover:text-white text-sm transition-colors hover:underline"
                        >
                            {mode === 'LOGIN' ? 'ليس لديك حساب؟ سجل الآن' : 'لديك حساب بالفعل؟ سجل الدخول'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AuthModal;
