"""
World engine for Project Genesis.
Manages the 2D cellular world with terrain, resources, and dynamic generation.
"""

import numpy as np
import noise
from typing import Dict, Tuple, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import random
import math


class TerrainType(Enum):
    """Types of terrain in the world"""
    WATER = 0
    GRASSLAND = 1
    FOREST = 2
    MOUNTAIN = 3
    DESERT = 4


@dataclass
class ClimateState:
    """Current climate conditions affecting the world"""
    temperature: float = 20.0  # Celsius
    humidity: float = 50.0     # Percentage
    wind_speed: float = 5.0    # km/h
    precipitation: float = 0.0  # mm


@dataclass
class Building:
    """A building constructed by agents"""
    id: str
    type: str
    position: Tuple[int, int]
    owner: Optional[str] = None
    resources: Dict[str, float] = field(default_factory=dict)
    durability: float = 100.0
    capacity: int = 1


class World:
    """Main world class managing terrain, resources, and environment"""
    
    def __init__(self, width: int = 64, height: int = 64, seed: int = 42):
        self.width = width
        self.height = height
        self.seed = seed
        
        # Initialize random generator
        self.rng = random.Random(seed)
        np.random.seed(seed)
        
        # Core world state
        self.terrain = np.zeros((height, width), dtype=np.int8)
        self.elevation = np.zeros((height, width), dtype=np.float32)
        self.temperature = np.zeros((height, width), dtype=np.float32)
        self.humidity = np.zeros((height, width), dtype=np.float32)
        
        # Resource distributions
        self.resources = {
            'water': np.zeros((height, width), dtype=np.float32),
            'food': np.zeros((height, width), dtype=np.float32),
            'berries': np.zeros((height, width), dtype=np.float32),
            'fish': np.zeros((height, width), dtype=np.float32),
            'wood': np.zeros((height, width), dtype=np.float32),
            'stone': np.zeros((height, width), dtype=np.float32),
            'metal': np.zeros((height, width), dtype=np.float32),
        }
        
        # Dynamic elements
        self.buildings = {}  # building_id -> Building
        self.climate = ClimateState()
        self.time = 0
        
        # Generate initial world
        self._generate_world()
    
    def _generate_world(self):
        """Generate realistic terrain and resource distributions using noise"""
        # Generate elevation map using Perlin noise
        scale = 0.1
        for y in range(self.height):
            for x in range(self.width):
                self.elevation[y, x] = noise.pnoise2(
                    x * scale, y * scale, 
                    octaves=6, persistence=0.5, 
                    lacunarity=2.0, base=self.seed
                )
        
        # Normalize elevation to 0-1
        self.elevation = (self.elevation + 1) / 2
        
        # Generate temperature based on latitude (simplified)
        for y in range(self.height):
            lat_temp = 30 - abs(y - self.height//2) * 0.8
            for x in range(self.width):
                self.temperature[y, x] = lat_temp + self.rng.gauss(0, 3)
        
        # Generate humidity based on elevation and temperature
        for y in range(self.height):
            for x in range(self.width):
                base_humidity = max(0, 100 - self.elevation[y, x] * 80)
                temp_factor = max(0, 1 - abs(self.temperature[y, x] - 20) / 30)
                self.humidity[y, x] = base_humidity * temp_factor + self.rng.gauss(0, 5)
        
        # Generate terrain based on elevation, temperature, humidity
        self._generate_terrain()
        
        # Generate resources based on terrain and environmental factors
        self._generate_resources()
    
    def _generate_terrain(self):
        """Convert environmental factors to terrain types"""
        for y in range(self.height):
            for x in range(self.width):
                elev = self.elevation[y, x]
                temp = self.temperature[y, x]
                humid = self.humidity[y, x]
                
                if elev < 0.3:  # Low elevation
                    self.terrain[y, x] = TerrainType.WATER.value
                elif elev > 0.8:  # High elevation
                    self.terrain[y, x] = TerrainType.MOUNTAIN.value
                elif temp > 30 and humid < 30:  # Hot and dry
                    self.terrain[y, x] = TerrainType.DESERT.value
                elif humid > 60 and temp > 10:  # Wet and warm
                    self.terrain[y, x] = TerrainType.FOREST.value
                else:  # Default
                    self.terrain[y, x] = TerrainType.GRASSLAND.value
    
    def _generate_resources(self):
        """Generate realistic resource distributions"""
        # Water is abundant near water terrain
        water_mask = (self.terrain == TerrainType.WATER.value)
        self.resources['water'] = self._generate_resource_cluster(
            water_mask, abundance=0.8, clustering=0.9
        )
        
        # Food is abundant in grassland and forest
        food_mask = np.isin(self.terrain, [TerrainType.GRASSLAND.value, TerrainType.FOREST.value])
        self.resources['food'] = self._generate_resource_cluster(
            food_mask, abundance=0.6, clustering=0.7
        )
        
        # Wood is abundant in forest
        wood_mask = (self.terrain == TerrainType.FOREST.value)
        self.resources['wood'] = self._generate_resource_cluster(
            wood_mask, abundance=0.7, clustering=0.8
        )
        
        # Stone is abundant in mountains
        stone_mask = (self.terrain == TerrainType.MOUNTAIN.value)
        self.resources['stone'] = self._generate_resource_cluster(
            stone_mask, abundance=0.5, clustering=0.9
        )
        
        # Metal is rare, mostly in mountains
        metal_mask = (self.terrain == TerrainType.MOUNTAIN.value)
        self.resources['metal'] = self._generate_resource_cluster(
            metal_mask, abundance=0.1, clustering=0.95
        )
    
    def _generate_resource_cluster(self, base_mask: np.ndarray, abundance: float, clustering: float) -> np.ndarray:
        """Generate clustered resource distribution"""
        # Start with base mask
        resource = base_mask.astype(float) * abundance
        
        # Add noise for natural variation
        noise_map = np.zeros_like(resource)
        scale = 0.1
        for y in range(self.height):
            for x in range(self.width):
                noise_map[y, x] = noise.pnoise2(
                    x * scale, y * scale, 
                    octaves=3, persistence=0.5, 
                    lacunarity=2.0, base=self.seed + 1000
                )
        
        # Apply clustering
        resource = resource + (noise_map + 1) / 2 * clustering
        
        # Normalize to 0-1
        if resource.max() > 0:
            resource = resource / resource.max()
        
        return np.clip(resource, 0, 1)
    
    def get_valid_spawn_positions(self, radius: int = 5) -> List[Tuple[int, int]]:
        """Get valid positions for agent spawning (land tiles)"""
        valid = []
        center_x, center_y = self.width // 2, self.height // 2
        
        for y in range(max(0, center_y - radius), min(self.height, center_y + radius)):
            for x in range(max(0, center_x - radius), min(self.width, center_x + radius)):
                if self.terrain[y, x] != TerrainType.WATER.value:
                    valid.append((x, y))
        
        return valid
    
    def get_resource_at(self, position: Tuple[int, int], resource_type: str) -> float:
        """Get amount of resource at given position"""
        x, y = position
        if 0 <= x < self.width and 0 <= y < self.height:
            return float(self.resources[resource_type][y, x])
        return 0.0
    
    def harvest_resource(self, position: Tuple[int, int], resource_type: str, amount: float) -> float:
        """Harvest resource from position, returns actual harvested amount"""
        available = self.get_resource_at(position, resource_type)
        harvested = min(available, amount)
        
        x, y = position
        self.resources[resource_type][y, x] -= harvested
        
        return harvested
    
    def get_terrain_at(self, position: Tuple[int, int]) -> TerrainType:
        """Get terrain type at position"""
        x, y = position
        if 0 <= x < self.width and 0 <= y < self.height:
            return TerrainType(self.terrain[y, x])
        return TerrainType.WATER
    
    def add_building(self, building: Building):
        """Add a building to the world"""
        self.buildings[building.id] = building
    
    def remove_building(self, building_id: str):
        """Remove a building from the world"""
        if building_id in self.buildings:
            del self.buildings[building_id]
    
    def get_building_at(self, position: Tuple[int, int]) -> Optional[Building]:
        """Get building at given position"""
        for building in self.buildings.values():
            if building.position == position:
                return building
        return None
    
    def update_climate(self):
        """Update climate based on time and world state"""
        self.time += 1
        
        # Simple climate cycles
        seasonal_temp = 20 + 10 * math.sin(2 * math.pi * self.time / 365)
        self.climate.temperature = seasonal_temp + self.rng.gauss(0, 2)
        
        # Update resource regeneration based on climate
        self._regenerate_resources()
    
    def _regenerate_resources(self):
        """Regenerate resources based on climate and terrain"""
        regen_rate = 0.001  # Base regeneration rate
        
        for resource_name in self.resources:
            if resource_name == 'water':
                # Water regenerates near water terrain
                water_mask = (self.terrain == TerrainType.WATER.value)
                self.resources['water'] = np.clip(
                    self.resources['water'] + water_mask * regen_rate * 2,
                    0, 1
                )
            elif resource_name == 'food':
                # Food regenerates based on climate and terrain
                growth_mask = np.isin(self.terrain, [TerrainType.GRASSLAND.value, TerrainType.FOREST.value])
                temp_factor = np.clip(1 - abs(self.temperature - 20) / 20, 0, 1)
                self.resources['food'] = np.clip(
                    self.resources['food'] + growth_mask * temp_factor * regen_rate,
                    0, 1
                )
    
    def get_world_summary(self) -> Dict[str, Any]:
        """Get summary of world state"""
        terrain_counts = {}
        for terrain_type in TerrainType:
            count = np.sum(self.terrain == terrain_type.value)
            terrain_counts[terrain_type.name] = count
        
        resource_totals = {}
        for resource_name, distribution in self.resources.items():
            resource_totals[resource_name] = float(np.sum(distribution))
        
        return {
            "dimensions": (self.width, self.height),
            "terrain_distribution": terrain_counts,
            "total_resources": resource_totals,
            "climate": {
                "temperature": self.climate.temperature,
                "humidity": self.climate.humidity,
            },
            "buildings": len(self.buildings),
            "time": self.time,
        }
    
    def get_neighbors(self, position: Tuple[int, int], radius: int = 1) -> List[Tuple[int, int]]:
        """Get neighboring positions"""
        x, y = position
        neighbors = []
        
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue
                
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    neighbors.append((nx, ny))
        
        return neighbors
    
    def manhattan_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
        """Calculate Manhattan distance between two positions"""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
    
    def euclidean_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """Calculate Euclidean distance between two positions"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)


if __name__ == "__main__":
    # Test world generation
    world = World(32, 32, seed=12345)
    summary = world.get_world_summary()
    
    print("World Generation Test:")
    print(f"Dimensions: {summary['dimensions']}")
    print(f"Terrain: {summary['terrain_distribution']}")
    print(f"Resources: {summary['total_resources']}")
    print(f"Valid spawn positions: {len(world.get_valid_spawn_positions())}")