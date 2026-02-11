export class SoundManager {
    private ctx: AudioContext | null = null;
    private isMuted: boolean = false;

    constructor() {
        // Initialize AudioContext only on user interaction usually, but here we prep it
        try {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            this.ctx = new AudioContextClass();
        } catch (e) {
            console.error("Web Audio API not supported", e);
        }
    }

    public setMute(muted: boolean) {
        this.isMuted = muted;
    }

    private getContext(): AudioContext | null {
        if (!this.ctx) return null;
        if (this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
        return this.ctx;
    }

    // SFX: Card Flip / Play (Realistic "Snap")
    public playCardSound() {
        if (this.isMuted) return;
        const ctx = this.getContext();
        if (!ctx) return;

        const t = ctx.currentTime;

        // 1. Whitenoise "Swish" (Air resistance)
        const noiseBuffer = ctx.createBuffer(1, ctx.sampleRate * 0.1, ctx.sampleRate);
        const data = noiseBuffer.getChannelData(0);
        for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;

        const noise = ctx.createBufferSource();
        noise.buffer = noiseBuffer;

        const noiseFilter = ctx.createBiquadFilter();
        noiseFilter.type = 'lowpass';
        noiseFilter.frequency.setValueAtTime(1000, t);
        noiseFilter.frequency.linearRampToValueAtTime(100, t + 0.1);

        const noiseGain = ctx.createGain();
        noiseGain.gain.setValueAtTime(0.4, t);
        noiseGain.gain.exponentialRampToValueAtTime(0.01, t + 0.08);

        noise.connect(noiseFilter);
        noiseFilter.connect(noiseGain);
        noiseGain.connect(ctx.destination);
        noise.start(t);

        // 2. Card "Snap" (High pitched impulse)
        const osc = ctx.createOscillator();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(200, t);
        osc.frequency.exponentialRampToValueAtTime(40, t + 0.05);

        const oscGain = ctx.createGain();
        oscGain.gain.setValueAtTime(0.3, t);
        oscGain.gain.exponentialRampToValueAtTime(0.01, t + 0.05);

        osc.connect(oscGain);
        oscGain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.1);
    }

    // SFX: Shuffle (Rhythmic ripple)
    public playShuffleSound() {
        if (this.isMuted) return;
        this.playCardSound(); // Just one crisp sound, or a controlled burst
    }

    public playDealSequence() {
        if (this.isMuted) return;
        // Rapid succession of card sounds
        let count = 0;
        const interval = setInterval(() => {
            this.playCardSound();
            count++;
            if (count > 5) clearInterval(interval);
        }, 80);
    }

    // SFX: Success / Win Trick (Gold Coin Chime)
    public playWinSound() {
        if (this.isMuted) return;
        const ctx = this.getContext();
        if (!ctx) return;

        const t = ctx.currentTime;

        // Primary Bell
        const osc = ctx.createOscillator();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, t); // A5
        osc.frequency.exponentialRampToValueAtTime(880, t + 1);

        const gain = ctx.createGain();
        gain.gain.setValueAtTime(0.2, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 1.5);

        // Harmonics for "shine"
        const osc2 = ctx.createOscillator();
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(1760, t); // A6

        const gain2 = ctx.createGain();
        gain2.gain.setValueAtTime(0.1, t);
        gain2.gain.exponentialRampToValueAtTime(0.001, t + 1.0);

        osc.connect(gain);
        osc2.connect(gain2);
        gain.connect(ctx.destination);
        gain2.connect(ctx.destination);

        osc.start(t);
        osc2.start(t);
        osc.stop(t + 2);
        osc2.stop(t + 2);
    }

    // SFX: Your Turn (Glassy "Ding")
    public playTurnSound() {
        if (this.isMuted) return;
        const ctx = this.getContext();
        if (!ctx) return;

        const t = ctx.currentTime;
        const osc = ctx.createOscillator();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(1200, t);

        const gain = ctx.createGain();
        gain.gain.setValueAtTime(0, t);
        gain.gain.linearRampToValueAtTime(0.3, t + 0.05); // Soft attack
        gain.gain.exponentialRampToValueAtTime(0.001, t + 1.0); // Long decay

        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 1.2);
    }

    // SFX: Error / Invalid Move (Low Buzz)
    public playErrorSound() {
        if (this.isMuted) return;
        const ctx = this.getContext();
        if (!ctx) return;

        const t = ctx.currentTime;
        const osc = ctx.createOscillator();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(150, t);
        osc.frequency.linearRampToValueAtTime(100, t + 0.3);

        const gain = ctx.createGain();
        gain.gain.setValueAtTime(0.2, t);
        gain.gain.linearRampToValueAtTime(0.01, t + 0.3);

        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.3);
    }
    // SFX: Project Declaration (Wow effect)
    public playProjectSound() {
        if (this.isMuted) return;
        const ctx = this.getContext();
        if (!ctx) return;
        const t = ctx.currentTime;

        // Ascending harp-like arpeggio
        const frequencies = [440, 554, 659, 880]; // A major
        frequencies.forEach((f, i) => {
            const osc = ctx.createOscillator();
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(f, t + i * 0.1);

            const gain = ctx.createGain();
            gain.gain.setValueAtTime(0, t + i * 0.1);
            gain.gain.linearRampToValueAtTime(0.2, t + i * 0.1 + 0.05);
            gain.gain.exponentialRampToValueAtTime(0.001, t + i * 0.1 + 1.0);

            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(t + i * 0.1);
            osc.stop(t + i * 0.1 + 1.2);
        });
    }

    // SFX: Akka Declaration (Strong Impact)
    public playAkkaSound() {
        if (this.isMuted) return;
        const ctx = this.getContext();
        if (!ctx) return;
        const t = ctx.currentTime;

        // "Akka" - Two hits? Or one strong hit? 
        // Let's do a strong "Boom-Chime"

        // Low boom
        const osc1 = ctx.createOscillator();
        osc1.type = 'sawtooth';
        osc1.frequency.setValueAtTime(110, t); // A2
        osc1.frequency.exponentialRampToValueAtTime(55, t + 0.3);

        const gain1 = ctx.createGain();
        gain1.gain.setValueAtTime(0.5, t);
        gain1.gain.exponentialRampToValueAtTime(0.01, t + 0.5);

        // High chime
        const osc2 = ctx.createOscillator();
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(880, t); // A5
        osc2.frequency.exponentialRampToValueAtTime(1760, t + 0.1);

        const gain2 = ctx.createGain();
        gain2.gain.setValueAtTime(0.3, t);
        gain2.gain.exponentialRampToValueAtTime(0.01, t + 0.5);

        osc1.connect(gain1);
        osc2.connect(gain2);
        gain1.connect(ctx.destination);
        gain2.connect(ctx.destination);

        osc1.start(t);
        osc1.stop(t + 0.5);
        osc2.start(t);
        osc2.stop(t + 0.5);
    }

    // SFX: UI Click (Short mechanical tick)
    public playClick() {
        if (this.isMuted) return;
        const ctx = this.getContext();
        if (!ctx) return;
        const t = ctx.currentTime;

        const osc = ctx.createOscillator();
        osc.type = 'square';
        osc.frequency.setValueAtTime(800, t);
        osc.frequency.exponentialRampToValueAtTime(100, t + 0.05);

        const gain = ctx.createGain();
        gain.gain.setValueAtTime(0.1, t);
        gain.gain.exponentialRampToValueAtTime(0.01, t + 0.05);

        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.05);
    }
}

export const soundManager = new SoundManager();
