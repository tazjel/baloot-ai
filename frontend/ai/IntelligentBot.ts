/*
import * as ort from 'onnxruntime-web';
import { devLogger } from '../utils/devLogger';

export class IntelligentBot {
   // ... (Disabled for Debugging WASM Crash)
   constructor() {}
   async loadModel() { console.log("Bot AI Disabled"); }
   async predict() { return -1; }
}
*/

export class IntelligentBot {
    public session: any = null;
    constructor() { }
    async loadModel() { console.log("Bot AI Disabled (WASM Fix)"); }
    async predict(gameState: any, myIndex: number) { return -1; }
}
