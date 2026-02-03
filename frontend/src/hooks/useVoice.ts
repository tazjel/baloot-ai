import { useCallback, useRef } from 'react';

export type VoicePersonality = 'AGRESSIVE' | 'CONSERVATIVE' | 'BALANCED';

interface VoiceProfile {
    pitch: number;
    rate: number;
    lang: string;
}

const VOICES: Record<VoicePersonality, VoiceProfile> = {
    AGRESSIVE: { pitch: 1.1, rate: 1.25, lang: 'ar-SA' }, // Khalid: Fast, slightly high/tense
    CONSERVATIVE: { pitch: 0.8, rate: 0.85, lang: 'ar-SA' }, // Abu Fahad: Deep, slow, authoritative
    BALANCED: { pitch: 1.0, rate: 1.0, lang: 'ar-SA' }     // Saad: Normal
};

export const useVoice = () => {
    const synthesis = window.speechSynthesis;
    // Cache voices to avoid getVoices() lag
    const voicesRef = useRef<SpeechSynthesisVoice[]>([]);

    const speak = useCallback((text: string, personality: VoicePersonality = 'BALANCED') => {
        if (!synthesis) return;

        // Retry fetching voices if empty (browser async loading)
        if (voicesRef.current.length === 0) {
            voicesRef.current = synthesis.getVoices();
        }

        // Cancel current speech if any (to make it snappy trash talk, interrupting previous)
        synthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        const profile = VOICES[personality];

        utterance.pitch = profile.pitch;
        utterance.rate = profile.rate;
        utterance.lang = profile.lang;

        // Try to find a specific Arabic voice
        const arabicVoice = voicesRef.current.find(v => v.lang.includes('ar'));
        if (arabicVoice) {
            utterance.voice = arabicVoice;
        }

        synthesis.speak(utterance);
    }, [synthesis]);

    return { speak };
};
