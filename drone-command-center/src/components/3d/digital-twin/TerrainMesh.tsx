'use client';

import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { WorldGenerator } from '@/lib/world/world-generator';

const WORLD_SIZE = 100;
const TERRAIN_RES = 128;

export function useWorldData() {
  return useMemo(() => {
    const gen = new WorldGenerator({
      size: WORLD_SIZE,
      seed: 42,
      urbanDensity: 0.6,
      vegetationDensity: 0.7,
      waterLevel: 0.4,
      hilliness: 0.5,
    });
    
    const heightmap = gen.generateHeightmap(TERRAIN_RES);
    const mesh = gen.generateTerrainMesh(heightmap, TERRAIN_RES);
    const buildings = gen.generateBuildings(heightmap, TERRAIN_RES);
    const trees = gen.generateTrees(heightmap, TERRAIN_RES, buildings);
    const roads = gen.generateRoads(TERRAIN_RES);
    const water = gen.generateWater(TERRAIN_RES);
    
    return { heightmap, mesh, buildings, trees, roads, water, terrainRes: TERRAIN_RES, worldSize: WORLD_SIZE };
  }, []);
}

export default function TerrainMesh({ mesh }: { mesh: ReturnType<WorldGenerator['generateTerrainMesh']> }) {
  const ref = useRef<THREE.Mesh>(null);
  
  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(mesh.positions, 3));
    geo.setAttribute('normal', new THREE.BufferAttribute(mesh.normals, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(mesh.colors, 3));
    geo.setAttribute('uv', new THREE.BufferAttribute(mesh.uvs, 2));
    geo.setIndex(new THREE.BufferAttribute(mesh.indices, 1));
    geo.computeVertexNormals();
    return geo;
  }, [mesh]);

  return (
    <mesh ref={ref} geometry={geometry} frustumCulled={false}>
      <meshStandardMaterial
        vertexColors
        metalness={0.05}
        roughness={0.9}
        flatShading={false}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}