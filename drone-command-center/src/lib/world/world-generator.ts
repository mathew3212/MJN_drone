// =============================================================================
// Real-world Digital Twin Terrain Generator
// Procedural generation with realistic elevation, biomes, water, urban layout
// =============================================================================

export interface WorldConfig {
  size: number;
  seed: number;
  urbanDensity: number;       // 0-1
  vegetationDensity: number;  // 0-1
  waterLevel: number;         // 0-1
  hilliness: number;          // 0-1
}

export interface TerrainVertex {
  x: number;
  z: number;
  y: number;
  normal: [number, number, number];
  color: [number, number, number];
  u: number; // texture coord
  v: number;
}

export interface BuildingData {
  x: number;
  z: number;
  width: number;
  depth: number;
  height: number;
  floors: number;
  color: string;
  roofColor: string;
  hasWindows: boolean;
  type: 'residential' | 'commercial' | 'industrial' | 'skyscraper';
}

export interface TreeData {
  x: number;
  z: number;
  scale: number;
  type: 'pine' | 'oak' | 'palm' | 'bush';
}

export interface RoadData {
  points: [number, number][];
  width: number;
  lanes: number;
  type: 'highway' | 'main' | 'residential';
}

export interface WaterBody {
  vertices: [number, number][];
  type: 'river' | 'lake' | 'pond';
  y: number;
}

export class WorldGenerator {
  private rng: () => number;
  
  constructor(private config: WorldConfig) {
    this.rng = this.createRNG(config.seed);
  }

  private createRNG(seed: number): () => number {
    let s = seed % 2147483647;
    if (s <= 0) s += 2147483646;
    return () => {
      s = (s * 16807) % 2147483647;
      return (s - 1) / 2147483646;
    };
  }

  // Generate heightmap using layered noise
  generateHeightmap(size: number): Float32Array {
    const data = new Float32Array(size * size);
    const r = this.rng;
    const octaves = 6;
    const persistence = 0.5;
    
    // Seed offset for each octave
    const offsets: [number, number][] = [];
    for (let i = 0; i < octaves; i++) {
      offsets.push([r() * 1000, r() * 1000]);
    }

    for (let z = 0; z < size; z++) {
      for (let x = 0; x < size; x++) {
        let height = 0;
        let amplitude = 1;
        let frequency = 1;
        let maxValue = 0;

        for (let o = 0; o < octaves; o++) {
          const nx = (x + offsets[o][0]) / size * frequency;
          const nz = (z + offsets[o][1]) / size * frequency;
          const noise = this.smoothNoise(nx, nz);
          height += noise * amplitude;
          maxValue += amplitude;
          amplitude *= persistence;
          frequency *= 2;
        }

        height = height / maxValue;
        
        // Apply hilliness
        height = Math.pow(height, 1 + (1 - this.config.hilliness) * 2);
        
        // Apply urban flattening
        const cityCenterDist = Math.hypot(x / size - 0.5, z / size - 0.5);
        if (cityCenterDist < 0.2) {
          height *= cityCenterDist / 0.2 * 0.3;
        }

        data[z * size + x] = height * 30; // max 30m height
      }
    }
    return data;
  }

  private smoothNoise(x: number, y: number): number {
    const ix = Math.floor(x);
    const iy = Math.floor(y);
    const fx = x - ix;
    const fy = y - iy;
    
    const sx = fx * fx * (3 - 2 * fx);
    const sy = fy * fy * (3 - 2 * fy);

    const n00 = this.hash2D(ix, iy);
    const n10 = this.hash2D(ix + 1, iy);
    const n01 = this.hash2D(ix, iy + 1);
    const n11 = this.hash2D(ix + 1, iy + 1);

    const nx0 = n00 + (n10 - n00) * sx;
    const nx1 = n01 + (n11 - n01) * sx;
    
    return nx0 + (nx1 - nx0) * sy;
  }

  private hash2D(x: number, y: number): number {
    let h = x * 374761393 + y * 668265263;
    h = (h ^ (h >> 13)) * 1274126177;
    return (h & 0x7fffffff) / 0x7fffffff;
  }

  // Generate building data
  generateBuildings(heightmap: Float32Array, size: number): BuildingData[] {
    const buildings: BuildingData[] = [];
    const r = this.rng;
    const gridSize = Math.ceil(size / 8);
    const occupied = new Set<string>();

    for (let gz = 0; gz < gridSize; gz++) {
      for (let gx = 0; gx < gridSize; gx++) {
        if (r() > this.config.urbanDensity) continue;

        const cx = (gx + 0.5) * (size / gridSize);
        const cz = (gz + 0.5) * (size / gridSize);
        const dist = Math.hypot(cx / size - 0.5, cz / size - 0.5);

        // Only build on reasonable terrain
        const hi = Math.round(cz) * size + Math.round(cx);
        if (hi >= 0 && hi < heightmap.length && heightmap[hi] > 8) continue; // too steep
        if (dist > 0.45) continue; // edge of world

        const w = 3 + r() * 6;
        const d = 3 + r() * 6;
        const floors = dist < 0.15 
          ? Math.floor(10 + r() * 30)  // downtown skyscrapers
          : dist < 0.3 
          ? Math.floor(4 + r() * 8)    // midtown
          : Math.floor(1 + r() * 4);   // suburbs

        const height = floors * 3;
        const key = `${Math.round(cx / 4)},${Math.round(cz / 4)}`;
        if (occupied.has(key)) continue;
        occupied.add(key);

        const colors = [
          '#6B7280', '#4B5563', '#374151', '#5B6770', '#7C8B9E',
          '#8B9DAF', '#5A6B7C', '#3D4A5B',
        ];
        const roofColors = ['#3D4A5B', '#4A5A6B', '#5A6B7C', '#2D3A4B'];

        buildings.push({
          x: cx,
          z: cz,
          width: w,
          depth: d,
          height,
          floors,
          color: colors[Math.floor(r() * colors.length)],
          roofColor: roofColors[Math.floor(r() * roofColors.length)],
          hasWindows: true,
          type: floors > 15 ? 'skyscraper' : floors > 5 ? 'commercial' : 'residential',
        });
      }
    }
    return buildings;
  }

  // Generate trees
  generateTrees(heightmap: Float32Array, size: number, buildings: BuildingData[]): TreeData[] {
    const trees: TreeData[] = [];
    const r = this.rng;
    const occupied = new Set<string>();
    
    // Mark building footprints as occupied
    for (const b of buildings) {
      for (let dz = -b.depth / 2 - 1; dz < b.depth / 2 + 1; dz++) {
        for (let dx = -b.width / 2 - 1; dx < b.width / 2 + 1; dx++) {
          occupied.add(`${Math.round(b.x + dx)},${Math.round(b.z + dz)}`);
        }
      }
    }

    const count = Math.floor(size * size * 0.003 * this.config.vegetationDensity);
    let attempts = 0;
    while (trees.length < count && attempts < count * 3) {
      attempts++;
      const tx = r() * (size - 4) + 2;
      const tz = r() * (size - 4) + 2;
      const key = `${Math.round(tx)},${Math.round(tz)}`;
      
      if (occupied.has(key)) continue;

      const hi = Math.round(tz) * size + Math.round(tx);
      if (hi < 0 || hi >= heightmap.length) continue;
      const elev = heightmap[hi];
      if (elev > 5 || elev < -0.5) continue; // water or steep

      const dist = Math.hypot(tx / size - 0.5, tz / size - 0.5);
      const treeType: TreeData['type'] = 
        dist < 0.15 ? 'oak' :
        r() > 0.6 ? 'pine' :
        r() > 0.8 ? 'palm' : 'bush';

      trees.push({
        x: tx,
        z: tz,
        scale: 0.6 + r() * 0.8,
        type: treeType,
      });
      occupied.add(key);
    }
    return trees;
  }

  // Generate road network
  generateRoads(size: number): RoadData[] {
    const roads: RoadData[] = [];
    const r = this.rng;
    const spacing = 12;
    
    // Major roads (grid)
    for (let i = 2; i < size - 2; i += spacing) {
      roads.push({
        points: [[i, 0], [i, size]],
        width: 4,
        lanes: 2,
        type: 'main',
      });
    }
    for (let i = 2; i < size - 2; i += spacing) {
      roads.push({
        points: [[0, i], [size, i]],
        width: 4,
        lanes: 2,
        type: 'main',
      });
    }

    // Highway ring
    const ring: [number, number][] = [];
    const cx = size / 2;
    const cy = size / 2;
    const radius = size * 0.35;
    for (let i = 0; i <= 40; i++) {
      const angle = (i / 40) * Math.PI * 2;
      ring.push([cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius]);
    }
    roads.push({
      points: ring,
      width: 6,
      lanes: 4,
      type: 'highway',
    });

    return roads;
  }

  // Generate water bodies
  generateWater(size: number): WaterBody[] {
    const water: WaterBody[] = [];
    const r = this.rng;

    // River
    if (r() > 0.3) {
      const river: [number, number][] = [];
      let rx = r() * size * 0.3 + size * 0.1;
      let ry = 0;
      river.push([rx, ry]);
      for (let i = 0; i < size * 0.6; i++) {
        rx += r() * 1.5 - 0.75;
        ry += 1.5;
        river.push([rx, ry]);
      }
      water.push({ vertices: river, type: 'river', y: -0.3 });
    }

    // Lake
    if (r() > 0.5) {
      const lx = r() * size * 0.6 + size * 0.2;
      const lz = r() * size * 0.6 + size * 0.2;
      const lake: [number, number][] = [];
      const segments = 20;
      const lakeRadius = 5 + r() * 10;
      for (let i = 0; i <= segments; i++) {
        const angle = (i / segments) * Math.PI * 2;
        const noise = 0.8 + r() * 0.4;
        lake.push([
          lx + Math.cos(angle) * lakeRadius * noise,
          lz + Math.sin(angle) * lakeRadius * noise,
        ]);
      }
      water.push({ vertices: lake, type: 'lake', y: -0.3 });
    }

    return water;
  }

  // Compute terrain mesh vertices
  generateTerrainMesh(heightmap: Float32Array, size: number): { positions: Float32Array; normals: Float32Array; colors: Float32Array; uvs: Float32Array; indices: Uint16Array } {
    const positions = new Float32Array(size * size * 3);
    const normals = new Float32Array(size * size * 3);
    const colors = new Float32Array(size * size * 3);
    const uvs = new Float32Array(size * size * 2);

    // Calculate normals
    const getHeight = (x: number, z: number) => {
      if (x < 0 || x >= size || z < 0 || z >= size) return 0;
      return heightmap[z * size + x];
    };

    for (let z = 0; z < size; z++) {
      for (let x = 0; x < size; x++) {
        const i = z * size + x;
        const h = heightmap[i];
        
        positions[i * 3] = x - size / 2;
        positions[i * 3 + 1] = h;
        positions[i * 3 + 2] = z - size / 2;
        
        uvs[i * 2] = x / size;
        uvs[i * 2 + 1] = z / size;

        // Normal via central differences
        const hx1 = getHeight(x + 1, z);
        const hx2 = getHeight(x - 1, z);
        const hz1 = getHeight(x, z + 1);
        const hz2 = getHeight(x, z - 1);
        
        const nx = hx2 - hx1;
        const nz = hz2 - hz1;
        const len = Math.sqrt(nx * nx + 1 + nz * nz);
        
        normals[i * 3] = nx / len;
        normals[i * 3 + 1] = 1 / len;
        normals[i * 3 + 2] = nz / len;

        // Color based on height and biome
        const cityDist = Math.hypot(x / size - 0.5, z / size - 0.5);
        if (h < -0.2) {
          // Water - sandy
          colors[i * 3] = 0.6; colors[i * 3 + 1] = 0.5; colors[i * 3 + 2] = 0.3;
        } else if (h < 1) {
          // Grass
          const grassGreen = 0.35 + h * 0.1;
          colors[i * 3] = 0.2;
          colors[i * 3 + 1] = grassGreen;
          colors[i * 3 + 2] = 0.1;
        } else if (h < 5) {
          // Hills - brownish green
          const t = (h - 1) / 4;
          colors[i * 3] = 0.3 + t * 0.2;
          colors[i * 3 + 1] = 0.4 - t * 0.1;
          colors[i * 3 + 2] = 0.1 - t * 0.05;
        } else {
          // Mountains - rocky
          const t = Math.min(1, (h - 5) / 10);
          colors[i * 3] = 0.5 + t * 0.2;
          colors[i * 3 + 1] = 0.45 + t * 0.2;
          colors[i * 3 + 2] = 0.35 + t * 0.15;
        }
        
        // City center pavement tint
        if (cityDist < 0.2) {
          colors[i * 3] = Math.min(1, colors[i * 3] + 0.1);
          colors[i * 3 + 1] = Math.min(1, colors[i * 3 + 1] + 0.1);
          colors[i * 3 + 2] = Math.min(1, colors[i * 3 + 2] + 0.1);
        }
      }
    }

    // Index buffer
    const indices = new Uint16Array((size - 1) * (size - 1) * 6);
    let idx = 0;
    for (let z = 0; z < size - 1; z++) {
      for (let x = 0; x < size - 1; x++) {
        const a = z * size + x;
        const b = z * size + x + 1;
        const c = (z + 1) * size + x;
        const d = (z + 1) * size + x + 1;
        indices[idx++] = a;
        indices[idx++] = c;
        indices[idx++] = b;
        indices[idx++] = b;
        indices[idx++] = c;
        indices[idx++] = d;
      }
    }

    return { positions, normals, colors, uvs, indices };
  }
}