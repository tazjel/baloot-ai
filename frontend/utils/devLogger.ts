
// Simple Event-based Logger for Sidebar
type LogLevel = 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS';

export interface LogEntry {
    id: string;
    timestamp: string;
    level: LogLevel;
    category: string;
    message: string;
    data?: unknown;
}

class DevLogger {
    private logs: LogEntry[] = [];
    private listeners: ((log: LogEntry) => void)[] = [];
    private maxLogs = 100;

    log(category: string, message: string, data?: unknown) {
        this.addLog('INFO', category, message, data);
    }

    warn(category: string, message: string, data?: unknown) {
        this.addLog('WARN', category, message, data);
    }

    error(category: string, message: string, data?: unknown) {
        this.addLog('ERROR', category, message, data);
    }

    success(category: string, message: string, data?: unknown) {
        this.addLog('SUCCESS', category, message, data);
    }

    private socket: any = null; // Leaving as any or specific Socket type if imported

    setSocket(socket: any) {
        this.socket = socket;
    }

    private addLog(level: LogLevel, category: string, message: string, data?: unknown) {
        const entry: LogEntry = {
            id: Math.random().toString(36).substr(2, 9),
            timestamp: new Date().toLocaleTimeString(),
            level,
            category,
            message,
            data
        };

        this.logs.push(entry);
        if (this.logs.length > this.maxLogs) {
            this.logs.shift();
        }

        // Notify listeners
        this.listeners.forEach(l => l(entry));

        // Stream to Server (Telemetry)
        // Stream to Server (Telemetry)
        if (this.socket) {
            // Send everything to server for analysis (Agent Request)
            // Filter out extremely noisy stuff if needed, but for now send all.
            try {
                this.socket.emit('client_log', entry);
            } catch (e) { /* ignore */ }
        }

        // Also log to console for backup
        const style = level === 'ERROR' ? 'color: red' : level === 'WARN' ? 'color: orange' : level === 'SUCCESS' ? 'color: green' : 'color: blue';
        console.log(`%c[${category}] ${message}`, style, data || '');
    }

    subscribe(listener: (log: LogEntry) => void) {
        this.listeners.push(listener);
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }

    getHistory() {
        return [...this.logs];
    }

    clear() {
        this.logs = [];
        // Notify clear? Or just let UI handle it on next update?
        // Ideally emit a clear event or just let UI refresh.
        // For simplicity, we won't emit a special clear event strictly yet, 
        // but UI usually just appends. 
        // Let's add a special 'CLEAR' event handling if needed, or just let UI call getHistory().
    }
}

export const devLogger = new DevLogger();
