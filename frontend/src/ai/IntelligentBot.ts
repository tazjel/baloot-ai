import { devLogger } from '../utils/devLogger';

/**
 * Stub IntelligentBot — AI model loading is currently disabled.
 * This placeholder prevents WASM crashes while keeping the interface intact.
 */
export class IntelligentBot {
    public session: any = null;
    constructor() { }
    async loadModel() { devLogger.log('BOT', 'Bot AI Disabled (WASM Fix)'); }
    async predict(gameState: any, myIndex: number) { return -1; }
}
