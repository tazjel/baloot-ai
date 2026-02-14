declare global {
    interface Window {
        webkitAudioContext: typeof AudioContext;
    }
}

export class SoundManager {
    private ctx: AudioContext | null = null;
    private isMuted: boolean = false;
    private volumes: Record<string, number> = { cards: 1, ui: 1, events: 1, bids: 1 };

    constructor() {
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

    public setVolume(category: string, vol: number) {
        this.volumes[category] = Math.max(0, Math.min(1, vol));
    }

    public getVolume(category: string): number {
        return this.volumes[category] ?? 1;
    }

    private getContext(): AudioContext | null {
        if (!this.ctx) return null;
        if (this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
        return this.ctx;
    }

    private vol(category: string): number {
        return this.volumes[category] ?? 1;
    }

    // ========================================
    // EXISTING SOUNDS (with volume categories)
    // ========================================

    // SFX: Card Flip / Play (Realistic "Snap")
    public playCardSound() {
        if (this.isMuted) return;
        const ctx = this.getContext();
        if (!ctx) return;
        const v = this.vol('cards');
        if (v === 0) return;

        const t = ctx.currentTime;

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
        noiseGain.gain.setValueAtTime(0.4 * v, t);
        noiseGain.gain.exponentialRampToValueAtTime(0.01, t + 0.08);

        noise.connect(noiseFilter);
        noiseFilter.connect(noiseGain);
        noiseGain.connect(ctx.destination);
        noise.start(t);

        const osc = ctx.createOscillator();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(200, t);
        osc.frequency.exponentialRampToValueAtTime(40, t + 0.05);

        const oscGain = ctx.createGain();
        oscGain.gain.setValueAtTime(0.3 * v, t);
        oscGain.gain.exponentialRampToValueAtTime(0.01, t + 0.05);

        osc.connect(oscGain);
        oscGain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.1);
    }

    public playShuffleSound() {
        if (this.isMuted) return;
        this.playCardSound();
    }

    public playDealSequence() {
        if (this.isMuted) return;
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
        const v = this.vol('events');
        if (v === 0) return;

        const t = ctx.currentTime;

        const osc = ctx.createOscillator();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, t);

        const gain = ctx.createGain();
        gain.gain.setValueAtTime(0.2 * v, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 1.5);

        const osc2 = ctx.createOscillator();
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(1760, t);

        const gain2 = ctx.createGain();
        gain2.gain.setValueAtTime(0.1 * v, t);
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
        const v = this.vol('ui');
        if (v === 0) return;

        const t = ctx.currentTime;
        const osc = ctx.createOscillator();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(1200, t);

        const gain = ctx.createGain();
        gain.gain.setValueAtTime(0, t);
        gain.gain.linearRampToValueAtTime(0.3 * v, t + 0.05);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 1.0);

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
        const v = this.vol('ui');
        if (v === 0) return;

        const t = ctx.currentTime;
        const osc = ctx.createOscillator();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(150, t);
        osc.frequency.linearRampToValueAtTime(100, t + 0.3);

        const gain = ctx.createGain();
        gain.gain.setValueAtTime(0.2 * v, t);
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
        const v = this.vol('events');
        if (v === 0) return;
        const t = ctx.currentTime;

        const frequencies = [440, 554, 659, 880];
        frequencies.forEach((f, i) => {
            const osc = ctx.createOscillator();
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(f, t + i * 0.1);

            const gain = ctx.createGain();
            gain.gain.setValueAtTime(0, t + i * 0.1);
            gain.gain.linearRampToValueAtTime(0.2 * v, t + i * 0.1 + 0.05);
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
        const v = this.vol('events');
        if (v === 0) return;
        const t = ctx.currentTime;

        const osc1 = ctx.createOscillator();
        osc1.type = 'sawtooth';
        osc1.frequency.setValueAtTime(110, t);
        osc1.frequency.exponentialRampToValueAtTime(55, t + 0.3);

        const gain1 = ctx.createGain();
        gain1.gain.setValueAtTime(0.5 * v, t);
        gain1.gain.exponentialRampToValueAtTime(0.01, t + 0.5);

        const osc2 = ctx.createOscillator();
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(880, t);
        osc2.frequency.exponentialRampToValueAtTime(1760, t + 0.1);

        const gain2 = ctx.createGain();
        gain2.gain.setValueAtTime(0.3 * v, t);
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
        const v = this.vol('ui');
        if (v === 0) return;
        const t = ctx.currentTime;

        const osc = ctx.createOscillator();
        osc.type = 'square';
        osc.frequency.setValueAtTime(800, t);
        osc.frequency.exponentialRampToValueAtTime(100, t + 0.05);

        const gain = ctx.createGain();
        gain.gain.setValueAtTime(0.1 * v, t);
        gain.gain.exponentialRampToValueAtTime(0.01, t + 0.05);

        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.05);
    }

    // ========================================
    // M18: NEW BID SOUNDS
    // ========================================

    // SFX: Pass — Low muted triangle, quick decay
    public playPassSound() {
        if (this.isMuted) return;
        const ctx = this.getContext();
        if (!ctx) return;
        const v = this.vol('bids');
        if (v === 0) return;
        const t = ctx.currentTime;

        const osc = ctx.createOscillator();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(80, t);
        osc.frequency.exponentialRampToValueAtTime(40, t + 0.15);

        const filter = ctx.createBiquadFilter();
        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(200, t);

        const gain = ctx.createGain();
        gain.gain.setValueAtTime(0.15 * v, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.15);

        osc.connect(filter);
        filter.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.2);
    }

    // SFX: Hokum bid — Bold sine with harmonic
    public playHokumSound() {
        if (this.isMuted) return;
        const ctx = this.getContext();
        if (!ctx) return;
        const v = this.vol('bids');
        if (v === 0) return;
        const t = ctx.currentTime;

        const osc1 = ctx.createOscillator();
        osc1.type = 'sine';
        osc1.frequency.setValueAtTime(660, t);

        const osc2 = ctx.createOscillator();
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(1320, t);

        const gain1 = ctx.createGain();
        gain1.gain.setValueAtTime(0.25 * v, t);
        gain1.gain.exponentialRampToValueAtTime(0.001, t + 0.4);

        const gain2 = ctx.createGain();
        gain2.gain.setValueAtTime(0.12 * v, t);
        gain2.gain.exponentialRampToValueAtTime(0.001, t + 0.3);

        osc1.connect(gain1);
        osc2.connect(gain2);
        gain1.connect(ctx.destination);
        gain2.connect(ctx.destination);

        osc1.start(t);
        osc2.start(t);
        osc1.stop(t + 0.5);
        osc2.stop(t + 0.4);
    }

    // SFX: Sun bid — 3-note ascending arpeggio C6-E6-G6
    public playSunSound() {
        if (this.isMuted) return;
        const ctx = this.getContext();
        if (!ctx) return;
        const v = this.vol('bids');
        if (v === 0) return;
        const t = ctx.currentTime;

        const notes = [1047, 1319, 1568]; // C6, E6, G6
        notes.forEach((freq, i) => {
            const osc = ctx.createOscillator();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, t + i * 0.08);

            const gain = ctx.createGain();
            gain.gain.setValueAtTime(0, t + i * 0.08);
            gain.gain.linearRampToValueAtTime(0.2 * v, t + i * 0.08 + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.001, t + i * 0.08 + 0.4);

            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(t + i * 0.08);
            osc.stop(t + i * 0.08 + 0.5);
        });
    }

    // SFX: Double — Deep sawtooth snap with noise burst
    public playDoubleSound() {
        if (this.isMuted) return;
        const ctx = this.getContext();
        if (!ctx) return;
        const v = this.vol('bids');
        if (v === 0) return;
        const t = ctx.currentTime;

        // Deep sawtooth
        const osc = ctx.createOscillator();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(60, t);
        osc.frequency.exponentialRampToValueAtTime(30, t + 0.2);

        const oscGain = ctx.createGain();
        oscGain.gain.setValueAtTime(0.3 * v, t);
        oscGain.gain.exponentialRampToValueAtTime(0.001, t + 0.25);

        osc.connect(oscGain);
        oscGain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.3);

        // White noise snap
        const buf = ctx.createBuffer(1, ctx.sampleRate * 0.05, ctx.sampleRate);
        const d = buf.getChannelData(0);
        for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;

        const noiseSrc = ctx.createBufferSource();
        noiseSrc.buffer = buf;

        const bandpass = ctx.createBiquadFilter();
        bandpass.type = 'bandpass';
        bandpass.frequency.setValueAtTime(800, t);
        bandpass.Q.setValueAtTime(2, t);

        const noiseGain = ctx.createGain();
        noiseGain.gain.setValueAtTime(0.2 * v, t);
        noiseGain.gain.exponentialRampToValueAtTime(0.001, t + 0.05);

        noiseSrc.connect(bandpass);
        bandpass.connect(noiseGain);
        noiseGain.connect(ctx.destination);
        noiseSrc.start(t);
    }

    // ========================================
    // M18: KABOOT CELEBRATION SOUND
    // ========================================

    // SFX: Kaboot — Deep bass + brass chord
    public playKabootSound() {
        if (this.isMuted) return;
        const ctx = this.getContext();
        if (!ctx) return;
        const v = this.vol('events');
        if (v === 0) return;
        const t = ctx.currentTime;

        // Deep bass
        const bass = ctx.createOscillator();
        bass.type = 'sine';
        bass.frequency.setValueAtTime(55, t);

        const bassGain = ctx.createGain();
        bassGain.gain.setValueAtTime(0.4 * v, t);
        bassGain.gain.exponentialRampToValueAtTime(0.001, t + 0.8);

        bass.connect(bassGain);
        bassGain.connect(ctx.destination);
        bass.start(t);
        bass.stop(t + 1);

        // Brass chord (A4, C#5, E5, A5)
        const brassNotes = [440, 554, 659, 880];
        brassNotes.forEach((freq, i) => {
            const osc = ctx.createOscillator();
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(freq, t + 0.05);

            const filter = ctx.createBiquadFilter();
            filter.type = 'lowpass';
            filter.frequency.setValueAtTime(2000, t + 0.05);
            filter.frequency.exponentialRampToValueAtTime(500, t + 0.8);

            const gain = ctx.createGain();
            gain.gain.setValueAtTime(0, t + 0.05);
            gain.gain.linearRampToValueAtTime(0.12 * v, t + 0.1);
            gain.gain.exponentialRampToValueAtTime(0.001, t + 1.0);

            osc.connect(filter);
            filter.connect(gain);
            gain.connect(ctx.destination);
            osc.start(t + 0.05);
            osc.stop(t + 1.2);
        });
    }

    // ========================================
    // M18: VICTORY / DEFEAT JINGLES
    // ========================================

    // SFX: Victory — Ascending C5-E5-G5-C6 major arpeggio
    public playVictoryJingle() {
        if (this.isMuted) return;
        const ctx = this.getContext();
        if (!ctx) return;
        const v = this.vol('events');
        if (v === 0) return;
        const t = ctx.currentTime;

        const notes = [523, 659, 784, 1047]; // C5, E5, G5, C6
        notes.forEach((freq, i) => {
            const osc = ctx.createOscillator();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, t + i * 0.15);

            // Add shimmer harmonic
            const osc2 = ctx.createOscillator();
            osc2.type = 'triangle';
            osc2.frequency.setValueAtTime(freq * 2, t + i * 0.15);

            const gain = ctx.createGain();
            gain.gain.setValueAtTime(0, t + i * 0.15);
            gain.gain.linearRampToValueAtTime(0.2 * v, t + i * 0.15 + 0.03);
            gain.gain.exponentialRampToValueAtTime(0.001, t + i * 0.15 + 0.6);

            const gain2 = ctx.createGain();
            gain2.gain.setValueAtTime(0, t + i * 0.15);
            gain2.gain.linearRampToValueAtTime(0.08 * v, t + i * 0.15 + 0.03);
            gain2.gain.exponentialRampToValueAtTime(0.001, t + i * 0.15 + 0.4);

            osc.connect(gain);
            osc2.connect(gain2);
            gain.connect(ctx.destination);
            gain2.connect(ctx.destination);
            osc.start(t + i * 0.15);
            osc2.start(t + i * 0.15);
            osc.stop(t + i * 0.15 + 0.8);
            osc2.stop(t + i * 0.15 + 0.5);
        });
    }

    // SFX: Defeat — Descending C5-Bb4-G4-Eb4 minor, slightly detuned
    public playDefeatJingle() {
        if (this.isMuted) return;
        const ctx = this.getContext();
        if (!ctx) return;
        const v = this.vol('events');
        if (v === 0) return;
        const t = ctx.currentTime;

        const notes = [523, 466, 392, 311]; // C5, Bb4, G4, Eb4
        notes.forEach((freq, i) => {
            const osc = ctx.createOscillator();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq - 2, t + i * 0.18); // slight detune

            const osc2 = ctx.createOscillator();
            osc2.type = 'sine';
            osc2.frequency.setValueAtTime(freq + 2, t + i * 0.18); // opposite detune (chorus)

            const gain = ctx.createGain();
            gain.gain.setValueAtTime(0, t + i * 0.18);
            gain.gain.linearRampToValueAtTime(0.15 * v, t + i * 0.18 + 0.04);
            gain.gain.exponentialRampToValueAtTime(0.001, t + i * 0.18 + 0.7);

            const gain2 = ctx.createGain();
            gain2.gain.setValueAtTime(0, t + i * 0.18);
            gain2.gain.linearRampToValueAtTime(0.1 * v, t + i * 0.18 + 0.04);
            gain2.gain.exponentialRampToValueAtTime(0.001, t + i * 0.18 + 0.7);

            osc.connect(gain);
            osc2.connect(gain2);
            gain.connect(ctx.destination);
            gain2.connect(ctx.destination);
            osc.start(t + i * 0.18);
            osc2.start(t + i * 0.18);
            osc.stop(t + i * 0.18 + 0.8);
            osc2.stop(t + i * 0.18 + 0.8);
        });
    }
}

export const soundManager = new SoundManager();
