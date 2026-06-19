'use client';

import { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { BuildingData } from '@/lib/world/world-generator';

interface BuildingsProps {
  buildings: BuildingData[];
  terrainRes: number;
  worldSize: number;
}

export default function Buildings({ buildings, terrainRes, worldSize }: BuildingsProps) {
  const scale = worldSize / terrainRes;
  
  const dummy = useMemo(() => new THREE.Object3D(), []);

  return (
    <group>
      {buildings.map((b, i) => {
        const x = (b.x / terrainRes) * worldSize - worldSize / 2 + (b.width * scale) / 2;
        const z = (b.z / terrainRes) * worldSize - worldSize / 2 + (b.depth * scale) / 2;
        const w = b.width * scale;
        const d = b.depth * scale;
        const h = b.height;
        
        return (
          <group key={i} position={[x, h / 2, z]}>
            {/* Main building */}
            <mesh>
              <boxGeometry args={[w, h, d]} />
              <meshStandardMaterial
                color={b.color}
                metalness={0.3}
                roughness={0.7}
              />
            </mesh>
            {/* Roof */}
            <mesh position={[0, h / 2 + 0.1, 0]}>
              <boxGeometry args={[w * 1.02, 0.2, d * 1.02]} />
              <meshStandardMaterial color={b.roofColor} metalness={0.2} roughness={0.8} />
            </mesh>
            {/* Windows (front face only for perf) */}
            {b.hasWindows && b.type !== 'industrial' && (
              <mesh position={[0, 0, d / 2 + 0.02]}>
                <planeGeometry args={[w * 0.8, h * 0.7]} />
                <meshBasicMaterial
                  color="#88CCFF"
                  transparent
                  opacity={0.15 + (b.floors > 15 ? 0.1 : 0)}
                />
              </mesh>
            )}
            {/* Skyscraper antenna */}
            {b.type === 'skyscraper' && (
              <mesh position={[0, h / 2 + 2, 0]}>
                <cylinderGeometry args={[0.05, 0.1, 4]} />
                <meshStandardMaterial color="#666" />
              </mesh>
            )}
            {/* Red hazard light on tall buildings */}
            {b.floors > 10 && (
              <mesh position={[0, h / 2 + 0.5, 0]}>
                <sphereGeometry args={[0.15, 8, 8]} />
                <meshBasicMaterial color="#FF3333" />
              </mesh>
            )}
          </group>
        );
      })}
    </group>
  );
}