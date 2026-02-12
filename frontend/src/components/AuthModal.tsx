import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { X } from 'lucide-react';

interface AuthModalProps {
    onClose: () => void;
}

const AuthModal: React.FC<AuthModalProps> = ({ onClose }) => {
    const { login, signup } = useAuth();
    const [isLogin, setIsLogin] = useState(true);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Form State
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);

        try {
            if (isLogin) {
                await login(email, password);
                onClose();
            } else {
                await signup(firstName, lastName, email, password);
                // After signup, switch to login or auto-login
                // For now, let's auto login or tell user to login
                // But backend signup doesn't return token, so we need to login
                setIsLogin(true);
                setError("Account created! Please sign in.");
                setIsLoading(false); // Stop loading but don't close
                return;
            }
        } catch (err: any) {
            setError(err.message || 'Authentication failed');
        } finally {
            if (isLogin) setIsLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="w-full max-w-md bg-zinc-900 border border-white/10 rounded-2xl p-6 relative">
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 text-white/50 hover:text-white"
                >
                    <X size={24} />
                </button>

                <div className="flex mb-6 border-b border-white/10">
                    <button
                        className={`flex-1 pb-3 font-bold text-lg ${isLogin ? 'text-yellow-400 border-b-2 border-yellow-400' : 'text-white/50'}`}
                        onClick={() => setIsLogin(true)}
                    >
                        Sign In
                    </button>
                    <button
                        className={`flex-1 pb-3 font-bold text-lg ${!isLogin ? 'text-yellow-400 border-b-2 border-yellow-400' : 'text-white/50'}`}
                        onClick={() => setIsLogin(false)}
                    >
                        Sign Up
                    </button>
                </div>

                {error && (
                    <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded text-red-200 text-sm">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                    {!isLogin && (
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs text-white/50 mb-1">First Name</label>
                                <input
                                    type="text"
                                    value={firstName}
                                    onChange={(e) => setFirstName(e.target.value)}
                                    className="w-full bg-black/50 border border-white/10 rounded p-2 text-white focus:border-yellow-400 outline-none"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-xs text-white/50 mb-1">Last Name</label>
                                <input
                                    type="text"
                                    value={lastName}
                                    onChange={(e) => setLastName(e.target.value)}
                                    className="w-full bg-black/50 border border-white/10 rounded p-2 text-white focus:border-yellow-400 outline-none"
                                    required
                                />
                            </div>
                        </div>
                    )}

                    <div>
                        <label className="block text-xs text-white/50 mb-1">Email</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="w-full bg-black/50 border border-white/10 rounded p-2 text-white focus:border-yellow-400 outline-none"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-xs text-white/50 mb-1">Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full bg-black/50 border border-white/10 rounded p-2 text-white focus:border-yellow-400 outline-none"
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full bg-yellow-400 hover:bg-yellow-300 text-black font-bold py-3 rounded-lg mt-6 transition-colors disabled:opacity-50"
                    >
                        {isLoading ? 'Please wait...' : (isLogin ? 'Sign In' : 'Create Account')}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default AuthModal;
