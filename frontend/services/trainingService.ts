import { GameState } from "../types";

const API_BASE = 'http://127.0.0.1:3005/react-py4web'; // Updated to match run_game_server.py port

export interface TrainingExample {
    contextHash: string;
    gameState: string;
    badMove: string;
    correctMove: string;
    reason: string;
    imageFilename?: string;
}

export const submitTrainingData = async (data: TrainingExample) => {
    try {
        console.log("[Studio-Service] Submitting Training Data...", data);
        const response = await fetch(`${API_BASE}/submit_training`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });
        return await response.json();
    } catch (error) {
        console.error("Failed to submit training data", error);
        throw error;
    }
};

export const getTrainingData = async () => {
    try {
        console.log("[Studio-Service] Fetching Training Data...");
        const response = await fetch(`${API_BASE}/training_data`);
        return await response.json();
    } catch (error) {
        console.error("Failed to fetch training data", error);
        return { data: [] };
    }
};

export const analyzeScreenshot = async (file: File) => {
    const formData = new FormData();
    formData.append('screenshot', file);

    try {
        console.log("[Studio-Service] Uploading Screenshot...", file.name);
        const response = await fetch(`${API_BASE}/analyze_screenshot`, {
            method: 'POST',
            body: formData,
        });
        return await response.json();
    } catch (error) {
        console.error("Failed to analyze screenshot", error);
        throw error;
    }
};

export const askStrategy = async (gameState: GameState) => {
    try {
        console.log("[Studio-Service] Asking AI Strategy...", gameState);
        const response = await fetch(`${API_BASE}/ask_strategy`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ gameState }),
        });
        return await response.json();
    } catch (error) {
        console.error("Failed to ask strategy", error);
        throw error;
    }
};

export const generateScenario = async (text: string) => {
    try {
        const response = await fetch(`${API_BASE}/generate_scenario`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        return await response.json();
    } catch (error) {
        console.error("Failed to generate scenario", error);
        throw error;
    }
};

export const analyzeMatch = async (gameId: string) => {
    try {
        const response = await fetch(`${API_BASE}/analyze_match`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ gameId })
        });
        return await response.json();
    } catch (error) {
        console.error("Failed to analyze match", error);
        throw error;
    }
};

export const getBrainMemory = async () => {
    try {
        console.log("[Studio-Service] Fetching Brain Memory...");
        const res = await fetch(`${API_BASE}/brain/memory`);
        return await res.json();
    } catch (error) {
        console.error("Error fetching brain memory:", error);
        return { error: "Network Error" };
    }
};

export const deleteBrainMemory = async (hash: string) => {
    try {
        const res = await fetch(`${API_BASE}/brain/memory/${hash}`, {
            method: 'DELETE'
        });
        return await res.json();
    } catch (error) {
        console.error("Error deleting brain memory:", error);
        return { error: "Network Error" };
    }
};
