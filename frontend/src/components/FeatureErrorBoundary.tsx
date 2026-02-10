import React, { Component, ErrorInfo, ReactNode } from 'react';
import { devLogger } from '../utils/devLogger';

interface Props {
    children: ReactNode;
    /** Human-readable section name for error context, e.g. "Table", "ActionBar" */
    featureName: string;
    /** Optional custom fallback. If not provided, a compact inline fallback is rendered. */
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

/**
 * Lightweight error boundary for wrapping individual UI sections.
 * Unlike the global ErrorBoundary (full-page takeover), this renders
 * a compact inline fallback so the rest of the app remains functional.
 */
class FeatureErrorBoundary extends Component<Props, State> {
    public state: State = { hasError: false, error: null };

    public static getDerivedStateFromError(error: Error): Partial<State> {
        return { hasError: true, error };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        devLogger.error('FeatureErrorBoundary', `[${this.props.featureName}] crashed`, {
            error: error.message,
            stack: errorInfo.componentStack,
        });
    }

    private handleRetry = () => {
        this.setState({ hasError: false, error: null });
    };

    public render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div
                    className="flex flex-col items-center justify-center gap-3 p-6 rounded-2xl"
                    style={{
                        background: 'rgba(0, 0, 0, 0.5)',
                        backdropFilter: 'blur(12px)',
                        border: '1px solid rgba(239, 68, 68, 0.25)',
                        minHeight: '120px',
                    }}
                >
                    <span className="text-2xl">⚠️</span>
                    <p className="text-sm text-red-400/90 text-center font-medium">
                        حدث خطأ في {this.props.featureName}
                    </p>
                    <button
                        onClick={this.handleRetry}
                        className="px-5 py-1.5 text-xs font-bold rounded-full
                                   bg-gradient-to-r from-amber-500 to-amber-600 text-black
                                   hover:from-amber-400 hover:to-amber-500
                                   transition-all shadow-md hover:shadow-lg
                                   active:scale-95"
                    >
                        🔄 إعادة المحاولة
                    </button>
                    {this.state.error && (
                        <details className="w-full max-w-xs">
                            <summary className="cursor-pointer text-[10px] text-gray-500 hover:text-gray-300 transition-colors text-center">
                                تفاصيل
                            </summary>
                            <pre className="mt-1 p-2 bg-black/60 rounded-lg text-[9px] text-red-300/70 overflow-auto max-h-20 font-mono border border-red-500/10">
                                {this.state.error.message}
                            </pre>
                        </details>
                    )}
                </div>
            );
        }

        return this.props.children;
    }
}

export default FeatureErrorBoundary;
