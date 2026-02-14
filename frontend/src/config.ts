/**
 * API base URL configuration.
 * Uses VITE_API_URL env var in production, falls back to localhost for dev.
 */
export const API_BASE_URL: string =
    (import.meta as any).env?.VITE_API_URL ||
    (window.location.hostname === 'localhost'
        ? 'http://localhost:3005'
        : `${window.location.protocol}//${window.location.hostname}:3005`);
