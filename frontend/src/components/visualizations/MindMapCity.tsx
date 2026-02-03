
import React, { useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text, Float, Stars, Environment } from '@react-three/drei';
import * as THREE from 'three';
import { interpolate } from 'maath/easing';

// Props:
// mindMap: { playerIdx: { cardIndex (0-31): probability (0-1) } }
// we need to map playerIdx to positions (Left, Top, Right) relative to bottom (0).

const CARD_NAMES = [
    "7S", "8S", "9S", "QS", "KS", "10S", "AS", "JS",
    "7H", "8H", "9H", "QH", "KH", "10H", "AH", "JH",
    "7C", "8C", "9C", "QC", "KC", "10C", "AC", "JC",
    "7D", "8D", "9D", "QD", "KD", "10D", "AD", "JD"
];

// Suits for coloring base
const SUIT_COLORS = {
    'S': '#1a1a1a', // Black
    'H': '#e53935', // Red
    'C': '#2e7d32', // Green
    'D': '#fbc02d'  // Yellow/Orange
};

function ProbabilityBar({ position, probability, label, index }) {
    const mesh = useRef();
    const lightRef = useRef();

    // Animate height
    useFrame((state, delta) => {
        if (!mesh.current) return;

        // Target scale: max height 5 units
        const targetHeight = Math.max(0.1, probability * 5);

        // Smoothly interpolate scale.y
        // mesh.current.scale.y = THREE.MathUtils.lerp(mesh.current.scale.y, targetHeight, delta * 3);
        // Using maath for better easing if installed, or simple lerp
        mesh.current.scale.y = THREE.MathUtils.damp(mesh.current.scale.y, targetHeight, 4, delta);

        // Position correction: scale grows from center, so we need to move y up
        mesh.current.position.y = mesh.current.scale.y / 2;

        // Color interpolation: Blue (Low) -> Red (High)
        // low: #2196f3, high: #ff0000
        const color = new THREE.Color().lerpColors(
            new THREE.Color('#2196f3'),
            new THREE.Color('#ff0000'),
            probability
        );
        mesh.current.material.color = color;

        // Light intensity based on probability
        if (lightRef.current) {
            lightRef.current.intensity = probability * 2;
            lightRef.current.color = color;
        }
    });

    return (
        <group position={position}>
            {/* The Bar */}
            <mesh ref={mesh} position={[0, 0.5, 0]}>
                <boxGeometry args={[0.2, 1, 0.2]} />
                <meshStandardMaterial roughnes={0.3} metalness={0.8} />
            </mesh>

            {/* Base Glow */}
            <pointLight ref={lightRef} position={[0, 0.2, 0]} distance={1} decay={2} />

            {/* Label (Only show if probability > 10% or if hovering) */}
            {probability > 0.1 && (
                <Text
                    position={[0, -0.3, 0]}
                    fontSize={0.15}
                    color="white"
                    anchorX="center"
                    anchorY="middle"
                >
                    {label}
                </Text>
            )}

            {/* Value Label (Top) */}
            {probability > 0.01 && (
                <Text
                    position={[0, probability * 5 + 0.3, 0]}
                    fontSize={0.12}
                    color="#ffd700"
                    anchorX="center"
                    anchorY="middle"
                >
                    {(probability * 100).toFixed(0)}%
                </Text>
            )}
        </group>
    );
}

function PlayerCity({ position, rotation, handData, playerName }) {
    // Layout indices 0-31 in a grid or line
    // Let's do 4 rows of 8 (Suits)

    const rows = [];
    for (let s = 0; s < 4; s++) { // Suits
        for (let r = 0; r < 8; r++) { // Ranks
            const idx = s * 8 + r;
            const prob = handData ? (handData[idx] || 0) : 0;
            const label = CARD_NAMES[idx];

            // X: Rank (spread out)
            // Z: Suit (depth)
            const x = (r - 3.5) * 0.4;
            const z = (s - 1.5) * 0.4;

            rows.push(
                <ProbabilityBar
                    key={idx}
                    position={[x, 0, z]}
                    probability={prob}
                    label={label}
                    index={idx}
                />
            );
        }
    }

    return (
        <group position={position} rotation={rotation}>
            <Float speed={2} rotationIntensity={0.1} floatIntensity={0.2}>
                <Text position={[0, 3, 0]} fontSize={0.5} color="#4fc3f7">
                    {playerName}
                </Text>
                <group position={[0, 0, 0]}>
                    {rows}
                </group>
                {/* Platform */}
                <mesh position={[0, -0.1, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                    <planeGeometry args={[4, 2]} />
                    <meshStandardMaterial color="#333" transparent opacity={0.5} />
                    <lineSegments>
                        <edgesGeometry args={[new THREE.PlaneGeometry(4, 2)]} />
                        <lineBasicMaterial color="#4fc3f7" />
                    </lineSegments>
                </mesh>
            </Float>
        </group>
    );
}

export default function MindMapCity({ mindMap, players }) {
    // mindMap: { 1: [probs...], 2: [probs...], 3: [probs...] }
    // players: Array of player objects to get names. 
    // Usually User is 0. 
    // Right is 1. Top is 2. Left is 3.

    return (
        <div style={{ width: '100%', height: '100%', background: '#000' }}>
            <Canvas camera={{ position: [0, 6, 8], fov: 45 }}>
                <color attach="background" args={['#050510']} />
                <fog attach="fog" args={['#050510', 5, 20]} />

                <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
                <ambientLight intensity={0.5} />
                <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} intensity={1} castShadow />
                <pointLight position={[-10, -10, -10]} intensity={0.5} color="blue" />

                <group position={[0, -1, 0]}>
                    {/* Right Player (Index 1) */}
                    <PlayerCity
                        position={[4, 0, 0]}
                        rotation={[0, -Math.PI / 4, 0]}
                        handData={mindMap && mindMap[1]}
                        playerName={players && players[1] ? players[1].name : "Right"}
                    />

                    {/* Top Player (Index 2 - Partner) */}
                    <PlayerCity
                        position={[0, 0, -3]}
                        rotation={[0, 0, 0]}
                        handData={mindMap && mindMap[2]}
                        playerName={players && players[2] ? players[2].name : "Top"}
                    />

                    {/* Left Player (Index 3) */}
                    <PlayerCity
                        position={[-4, 0, 0]}
                        rotation={[0, Math.PI / 4, 0]}
                        handData={mindMap && mindMap[3]}
                        playerName={players && players[3] ? players[3].name : "Left"}
                    />
                </group>

                <OrbitControls
                    enablePan={true}
                    enableZoom={true}
                    maxPolarAngle={Math.PI / 2 - 0.1}
                    autoRotate={true}
                    autoRotateSpeed={0.5}
                />
            </Canvas>
        </div>
    );
}
