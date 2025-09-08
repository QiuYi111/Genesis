"""Advanced terrain generation algorithms for realistic world maps

This module provides various terrain generation techniques:
1. Perlin Noise-based generation
2. Cellular Automata for natural cave systems and terrain smoothing
3. Voronoi diagrams for region-based terrain
4. Diamond-Square algorithm for heightmaps
5. River and water body generation
"""

import random
import math
import numpy as np
from typing import List, Dict, Tuple, Optional
from loguru import logger


class NoiseGenerator:
    """Perlin-like noise generator for natural terrain"""
    
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        
        # Generate permutation table for noise
        self.perm = list(range(256))
        random.shuffle(self.perm)
        self.perm = self.perm * 2  # Duplicate for easier indexing
    
    def fade(self, t: float) -> float:
        """Fade function for smooth interpolation"""
        return t * t * t * (t * (t * 6 - 15) + 10)
    
    def lerp(self, a: float, b: float, t: float) -> float:
        """Linear interpolation"""
        return a + t * (b - a)
    
    def grad(self, hash_val: int, x: float, y: float) -> float:
        """Gradient function"""
        h = hash_val & 15
        u = x if h < 8 else y
        v = y if h < 4 else (x if h == 12 or h == 14 else 0)
        return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)
    
    def noise(self, x: float, y: float) -> float:
        """Generate 2D Perlin noise"""
        # Find unit square coordinates
        X = int(x) & 255
        Y = int(y) & 255
        
        # Find relative x,y coordinates in square
        x -= int(x)
        y -= int(y)
        
        # Compute fade curves
        u = self.fade(x)
        v = self.fade(y)
        
        # Hash coordinates of square corners
        A = self.perm[X] + Y
        AA = self.perm[A]
        AB = self.perm[A + 1]
        B = self.perm[X + 1] + Y
        BA = self.perm[B]
        BB = self.perm[B + 1]
        
        # Blend results from corners
        return self.lerp(
            self.lerp(
                self.grad(self.perm[AA], x, y),
                self.grad(self.perm[BA], x - 1, y),
                u
            ),
            self.lerp(
                self.grad(self.perm[AB], x, y - 1),
                self.grad(self.perm[BB], x - 1, y - 1),
                u
            ),
            v
        )
    
    def octave_noise(self, x: float, y: float, octaves: int = 4, 
                    persistence: float = 0.5, lacunarity: float = 2.0) -> float:
        """Generate multi-octave noise"""
        value = 0.0
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0
        
        for _ in range(octaves):
            value += self.noise(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= lacunarity
        
        return value / max_value


class CellularAutomata:
    """Cellular automata for natural cave and terrain generation"""
    
    @staticmethod
    def generate_caves(width: int, height: int, initial_density: float = 0.45,
                      smoothing_iterations: int = 5) -> List[List[bool]]:
        """Generate cave-like patterns using cellular automata"""
        # Initialize with random noise
        grid = [[random.random() < initial_density for _ in range(width)] 
                for _ in range(height)]
        
        # Apply smoothing iterations
        for _ in range(smoothing_iterations):
            grid = CellularAutomata._smooth_iteration(grid)
        
        return grid
    
    @staticmethod
    def _smooth_iteration(grid: List[List[bool]]) -> List[List[bool]]:
        """Single smoothing iteration"""
        height, width = len(grid), len(grid[0])
        new_grid = [[False for _ in range(width)] for _ in range(height)]
        
        for y in range(height):
            for x in range(width):
                neighbor_count = CellularAutomata._count_neighbors(grid, x, y)
                # Rule: become wall if 4+ neighbors are walls
                new_grid[y][x] = neighbor_count >= 4
        
        return new_grid
    
    @staticmethod
    def _count_neighbors(grid: List[List[bool]], x: int, y: int) -> int:
        """Count wall neighbors (including out-of-bounds as walls)"""
        count = 0
        height, width = len(grid), len(grid[0])
        
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                if dx == 0 and dy == 0:
                    continue
                
                nx, ny = x + dx, y + dy
                if nx < 0 or nx >= width or ny < 0 or ny >= height:
                    count += 1  # Out of bounds counts as wall
                elif grid[ny][nx]:
                    count += 1
        
        return count


class VoronoiGenerator:
    """Voronoi diagram-based terrain generation"""
    
    @staticmethod
    def generate_regions(width: int, height: int, num_seeds: int, 
                        terrain_types: List[str]) -> Tuple[List[List[str]], List[Tuple[int, int]]]:
        """Generate terrain using Voronoi diagrams"""
        # Generate random seed points
        seeds = [(random.randint(0, width-1), random.randint(0, height-1)) 
                for _ in range(num_seeds)]
        
        # Assign terrain types to seeds
        seed_terrains = [random.choice(terrain_types) for _ in range(num_seeds)]
        
        # Create terrain map
        terrain_map = [["" for _ in range(width)] for _ in range(height)]
        
        for y in range(height):
            for x in range(width):
                # Find closest seed
                min_dist = float('inf')
                closest_seed = 0
                
                for i, (sx, sy) in enumerate(seeds):
                    dist = math.sqrt((x - sx)**2 + (y - sy)**2)
                    if dist < min_dist:
                        min_dist = dist
                        closest_seed = i
                
                terrain_map[y][x] = seed_terrains[closest_seed]
        
        return terrain_map, seeds


class TerrainGenerator:
    """Main terrain generator with multiple algorithms"""
    
    def __init__(self, seed: Optional[int] = None):
        self.noise = NoiseGenerator(seed)
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
    
    def generate_realistic_terrain(self, size: int, terrain_types: List[str], 
                                 terrain_colors: Dict[str, List[float]],
                                 algorithm: str = "noise") -> List[List[str]]:
        """Generate realistic terrain using specified algorithm"""
        
        if algorithm == "noise":
            return self._generate_noise_terrain(size, terrain_types)
        elif algorithm == "voronoi":
            return self._generate_voronoi_terrain(size, terrain_types)
        elif algorithm == "mixed":
            return self._generate_mixed_terrain(size, terrain_types)
        else:
            logger.warning(f"Unknown algorithm '{algorithm}', using noise")
            return self._generate_noise_terrain(size, terrain_types)
    
    def _generate_noise_terrain(self, size: int, terrain_types: List[str]) -> List[List[str]]:
        """Generate terrain using multi-octave noise"""
        terrain_map = [["" for _ in range(size)] for _ in range(size)]
        
        # Generate multiple noise layers for different terrain features
        elevation_map = self._generate_elevation_map(size)
        moisture_map = self._generate_moisture_map(size)
        temperature_map = self._generate_temperature_map(size)
        
        for y in range(size):
            for x in range(size):
                terrain_map[y][x] = self._classify_terrain(
                    elevation_map[y][x], 
                    moisture_map[y][x], 
                    temperature_map[y][x],
                    terrain_types
                )
        
        # Apply post-processing for more natural features
        terrain_map = self._add_rivers(terrain_map, elevation_map)
        terrain_map = self._smooth_terrain(terrain_map)
        
        return terrain_map
    
    def _generate_elevation_map(self, size: int) -> List[List[float]]:
        """Generate elevation using noise"""
        scale = 0.1
        elevation_map = [[0.0 for _ in range(size)] for _ in range(size)]
        
        for y in range(size):
            for x in range(size):
                elevation_map[y][x] = self.noise.octave_noise(
                    x * scale, y * scale, octaves=6, persistence=0.5
                )
        
        return elevation_map
    
    def _generate_moisture_map(self, size: int) -> List[List[float]]:
        """Generate moisture map using different noise parameters"""
        scale = 0.07
        moisture_map = [[0.0 for _ in range(size)] for _ in range(size)]
        
        for y in range(size):
            for x in range(size):
                moisture_map[y][x] = self.noise.octave_noise(
                    x * scale + 1000, y * scale + 1000, octaves=4, persistence=0.6
                )
        
        return moisture_map
    
    def _generate_temperature_map(self, size: int) -> List[List[float]]:
        """Generate temperature map with latitude effect"""
        scale = 0.05
        temperature_map = [[0.0 for _ in range(size)] for _ in range(size)]
        
        for y in range(size):
            for x in range(size):
                # Add latitude effect (colder towards edges)
                latitude_effect = 1.0 - abs(y - size/2) / (size/2)
                
                temperature_map[y][x] = (
                    self.noise.octave_noise(
                        x * scale + 2000, y * scale + 2000, octaves=3, persistence=0.4
                    ) * 0.3 + latitude_effect * 0.7
                )
        
        return temperature_map
    
    def _classify_terrain(self, elevation: float, moisture: float, 
                         temperature: float, terrain_types: List[str]) -> str:
        """Classify terrain based on elevation, moisture, and temperature"""
        
        # Define terrain classification rules
        if elevation < -0.3:
            return "OCEAN" if "OCEAN" in terrain_types else terrain_types[0]
        elif elevation < -0.1:
            return "RIVER" if "RIVER" in terrain_types else "GRASSLAND" if "GRASSLAND" in terrain_types else terrain_types[0]
        elif elevation > 0.4:
            if temperature < 0.3:
                return "MOUNTAIN" if "MOUNTAIN" in terrain_types else terrain_types[0]
            else:
                return "MOUNTAIN" if "MOUNTAIN" in terrain_types else terrain_types[0]
        else:
            # Mid-elevation terrain based on moisture and temperature
            if moisture > 0.3 and temperature > 0.4:
                return "FOREST" if "FOREST" in terrain_types else terrain_types[0]
            elif moisture < -0.2:
                return "DESERT" if "DESERT" in terrain_types else terrain_types[0]
            elif temperature < 0.2:
                return "TUNDRA" if "TUNDRA" in terrain_types else "GRASSLAND" if "GRASSLAND" in terrain_types else terrain_types[0]
            else:
                base = "GRASSLAND" if "GRASSLAND" in terrain_types else terrain_types[0]
                # Light randomization to avoid extreme skew when available
                if len(terrain_types) > 1 and random.random() < 0.01:
                    # pick a different terrain type to add variety
                    alt_choices = [t for t in terrain_types if t != base]
                    if alt_choices:
                        return random.choice(alt_choices)
                return base
    
    def _generate_voronoi_terrain(self, size: int, terrain_types: List[str]) -> List[List[str]]:
        """Generate terrain using Voronoi diagrams"""
        num_seeds = max(5, len(terrain_types) * 2)
        terrain_map, _ = VoronoiGenerator.generate_regions(size, size, num_seeds, terrain_types)
        return self._smooth_terrain(terrain_map)
    
    def _generate_mixed_terrain(self, size: int, terrain_types: List[str]) -> List[List[str]]:
        """Generate terrain using mixed algorithms"""
        # Start with noise-based base
        base_terrain = self._generate_noise_terrain(size, terrain_types)
        
        # Add some Voronoi regions for variety
        voronoi_terrain, seeds = VoronoiGenerator.generate_regions(
            size, size, len(terrain_types), terrain_types
        )
        
        # Blend the two maps
        blended_terrain = [["" for _ in range(size)] for _ in range(size)]
        
        for y in range(size):
            for x in range(size):
                # Use Voronoi in some areas, noise in others
                noise_val = self.noise.noise(x * 0.03, y * 0.03)
                if noise_val > 0.2:
                    blended_terrain[y][x] = voronoi_terrain[y][x]
                else:
                    blended_terrain[y][x] = base_terrain[y][x]
        
        return self._smooth_terrain(blended_terrain)
    
    def _add_rivers(self, terrain_map: List[List[str]], elevation_map: List[List[float]]) -> List[List[str]]:
        """Add rivers flowing from high to low elevation"""
        size = len(terrain_map)
        
        # Find high elevation points as river sources
        sources = []
        for y in range(size):
            for x in range(size):
                if elevation_map[y][x] > 0.3:
                    # Check if it's a local maximum
                    is_peak = True
                    for dy in range(-1, 2):
                        for dx in range(-1, 2):
                            ny, nx = y + dy, x + dx
                            if (0 <= ny < size and 0 <= nx < size and
                                elevation_map[ny][nx] > elevation_map[y][x]):
                                is_peak = False
                                break
                        if not is_peak:
                            break
                    
                    if is_peak and random.random() < 0.1:  # 10% chance for river source
                        sources.append((x, y))
        
        # Trace rivers from sources
        for sx, sy in sources:
            self._trace_river(terrain_map, elevation_map, sx, sy)
        
        return terrain_map
    
    def _trace_river(self, terrain_map: List[List[str]], elevation_map: List[List[float]], 
                    start_x: int, start_y: int):
        """Trace a river from source to lower elevation"""
        size = len(terrain_map)
        x, y = start_x, start_y
        visited = set()
        river_length = 0
        max_length = size // 4
        
        while river_length < max_length and (x, y) not in visited:
            visited.add((x, y))
            
            # Don't overwrite ocean or existing rivers
            if terrain_map[y][x] not in ["OCEAN", "RIVER"]:
                if random.random() < 0.7:  # 70% chance to place river tile
                    terrain_map[y][x] = "RIVER" if "RIVER" in [
                        terrain_map[i][j] for i in range(size) for j in range(size)
                    ] else terrain_map[y][x]
            
            # Find steepest descent direction
            best_direction = None
            min_elevation = elevation_map[y][x]
            
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    if dx == 0 and dy == 0:
                        continue
                    
                    nx, ny = x + dx, y + dy
                    if (0 <= nx < size and 0 <= ny < size and 
                        elevation_map[ny][nx] < min_elevation):
                        min_elevation = elevation_map[ny][nx]
                        best_direction = (dx, dy)
            
            if best_direction is None:
                break  # No downhill path found
            
            x += best_direction[0]
            y += best_direction[1]
            river_length += 1
    
    def _smooth_terrain(self, terrain_map: List[List[str]]) -> List[List[str]]:
        """Apply cellular automata-like smoothing to terrain"""
        size = len(terrain_map)
        smoothed_map = [row[:] for row in terrain_map]  # Deep copy
        
        for y in range(1, size - 1):
            for x in range(1, size - 1):
                # Count terrain types in neighborhood
                terrain_counts = {}
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        terrain = terrain_map[y + dy][x + dx]
                        terrain_counts[terrain] = terrain_counts.get(terrain, 0) + 1
                
                # If current terrain is very isolated, change to most common neighbor
                current_terrain = terrain_map[y][x]
                if terrain_counts.get(current_terrain, 0) <= 2:
                    most_common = max(terrain_counts.items(), key=lambda x: x[1])
                    if most_common[1] >= 5:  # Majority of neighbors
                        smoothed_map[y][x] = most_common[0]
        
        return smoothed_map


_TERRAIN_CACHE: Dict[Tuple[int, int, str, Tuple[str, ...]], List[List[str]]] = {}


def generate_advanced_terrain(size: int, terrain_types: List[str], 
                            terrain_colors: Dict[str, List[float]],
                            algorithm: str = "mixed", seed: Optional[int] = None) -> List[List[str]]:
    """Generate advanced terrain using specified algorithm
    
    Args:
        size: Map size (size x size)
        terrain_types: List of available terrain types
        terrain_colors: Color mapping for terrain types
        algorithm: Generation algorithm ("noise", "voronoi", "mixed")
        seed: Random seed for reproducible generation
        
    Returns:
        2D list representing the terrain map
    """
    # In-process cache keyed by (size, seed, algorithm, terrain_types)
    key = (size, seed or 0, algorithm, tuple(terrain_types))
    if key in _TERRAIN_CACHE:
        return _TERRAIN_CACHE[key]

    generator = TerrainGenerator(seed)
    terrain = generator.generate_realistic_terrain(size, terrain_types, terrain_colors, algorithm)
    _TERRAIN_CACHE[key] = terrain
    return terrain
