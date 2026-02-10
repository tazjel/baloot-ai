import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {

    public state: State = {
        hasError: false,
        error: null,
        errorInfo: null
    };

    public static getDerivedStateFromError(error: Error): Partial<State> {
        return { hasError: true, error };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('ErrorBoundary caught an error:', error, errorInfo);
        this.setState({ errorInfo });
    }

    private handleRetry = () => {
        this.setState({ hasError: false, error: null, errorInfo: null });
    };

    private handleGoToLobby = () => {
        // Clear state and reload to lobby
        window.location.hash = '';
        window.location.reload();
    };

    public render() {
        if (this.state.hasError) {
            return this.props.fallback || (
                <div className="w-full h-full flex flex-col items-center justify-center p-8"
                     style={{ background: 'linear-gradient(135deg, #1a0a0a 0%, #2d1010 50%, #1a0505 100%)' }}>
                    <div className="bg-black/60 backdrop-blur-xl rounded-3xl shadow-2xl p-8 max-w-lg w-full text-center border border-red-500/30">
                        {/* Error Icon */}
                        <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-red-500/20 to-red-800/20 border-2 border-red-500/40 flex items-center justify-center">
                            <span className="text-4xl">⚠️</span>
                        </div>

                        <h2 className="text-2xl font-bold text-red-400 mb-2 tracking-wide">عذراً، حدث خطأ ما</h2>
                        <p className="text-gray-400 mb-8 text-sm leading-relaxed">
                            حدث خطأ غير متوقع. يمكنك المحاولة مرة أخرى أو العودة للردهة.
                        </p>

                        {/* Action Buttons */}
                        <div className="flex flex-col sm:flex-row gap-3 justify-center mb-6">
                            <button
                                onClick={this.handleRetry}
                                className="px-8 py-3 bg-gradient-to-r from-amber-500 to-amber-600 text-black font-bold rounded-full hover:from-amber-400 hover:to-amber-500 transition-all shadow-lg shadow-amber-500/25 hover:shadow-amber-500/40 hover:scale-105 active:scale-95"
                            >
                                🔄 حاول مرة أخرى
                            </button>
                            <button
                                onClick={this.handleGoToLobby}
                                className="px-8 py-3 bg-white/10 text-white font-bold rounded-full hover:bg-white/20 transition-all border border-white/20 hover:border-white/40 hover:scale-105 active:scale-95"
                            >
                                🏠 العودة للردهة
                            </button>
                        </div>

                        {/* Error Details (Collapsible) */}
                        {this.state.error && (
                            <details className="mt-4 text-left">
                                <summary className="cursor-pointer text-xs text-gray-500 hover:text-gray-300 transition-colors select-none">
                                    📋 تفاصيل الخطأ (للمطورين)
                                </summary>
                                <pre className="mt-3 p-4 bg-black/60 rounded-xl text-[11px] text-red-300/80 overflow-auto max-h-40 border border-red-500/10 font-mono leading-relaxed">
                                    {this.state.error.toString()}
                                    {this.state.errorInfo?.componentStack && (
                                        <>
                                            {'\n\nComponent Stack:'}
                                            {this.state.errorInfo.componentStack}
                                        </>
                                    )}
                                </pre>
                            </details>
                        )}
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
