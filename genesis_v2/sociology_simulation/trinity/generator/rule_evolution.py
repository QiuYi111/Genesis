"""
Rule Evolution System - Dynamically evolves social rules, crafting recipes, and behavioral guidelines.

This system creates and updates rules based on observed agent behaviors and societal needs,
allowing for emergent social structures and cultural evolution.
"""

import json
import random
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

from loguru import logger


@dataclass
class SocialRule:
    """Represents a social rule or behavioral guideline"""
    rule_id: str
    name: str
    description: str
    category: str  # 'resource_sharing', 'territory', 'cooperation', 'conflict_resolution', 'trade'
    conditions: Dict[str, Any]  # when this rule applies
    consequences: Dict[str, Any]  # what happens when rule is followed/broken
    enforcement_level: float  # 0-1 how strictly enforced
    adoption_rate: float  # 0-1 how widely adopted
    emergence_reason: str
    based_on_pattern: str
    generation_turn: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'rule_id': self.rule_id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'conditions': self.conditions,
            'consequences': self.consequences,
            'enforcement_level': self.enforcement_level,
            'adoption_rate': self.adoption_rate,
            'emergence_reason': self.emergence_reason,
            'based_on_pattern': self.based_on_pattern,
            'generation_turn': self.generation_turn
        }


@dataclass
class CraftingRecipe:
    """Represents a crafting recipe that can be learned and used"""
    recipe_id: str
    name: str
    description: str
    ingredients: Dict[str, int]  # resource_name: quantity
    tools_required: List[str]  # tool types needed
    skill_required: str  # skill needed
    skill_level: float  # minimum skill level
    output: Dict[str, Any]  # what is produced
    complexity: float  # 0-1 complexity score
    efficiency: float  # resource efficiency multiplier
    generation_reason: str
    based_on_pattern: str
    generation_turn: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'recipe_id': self.recipe_id,
            'name': self.name,
            'description': self.description,
            'ingredients': self.ingredients,
            'tools_required': self.tools_required,
            'skill_required': self.skill_required,
            'skill_level': self.skill_level,
            'output': self.output,
            'complexity': self.complexity,
            'efficiency': self.efficiency,
            'generation_reason': self.generation_reason,
            'based_on_pattern': self.based_on_pattern,
            'generation_turn': self.generation_turn
        }


class RuleEvolution:
    """
    Evolves social rules and crafting recipes based on observed patterns.
    
    This system creates new rules and recipes that address societal needs,
    resource scarcity, cooperation opportunities, and conflict resolution.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.social_rules: List[SocialRule] = []
        self.crafting_recipes: List[CraftingRecipe] = []
        self.rule_templates = self._load_rule_templates()
        self.recipe_templates = self._load_recipe_templates()
        self.evolution_history: List[Dict[str, Any]] = []
        
        # Evolution parameters
        self.rule_threshold = config.get('rule_evolution_threshold', 5)
        self.recipe_threshold = config.get('recipe_evolution_threshold', 3)
        self.max_rules_per_category = config.get('max_rules_per_category', 8)
    
    def _load_rule_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load social rule templates"""
        return {
            'resource_sharing': [
                {
                    'name': 'Communal Resource Pool',
                    'description': 'Agents contribute excess resources to a shared pool',
                    'conditions': {'resource_excess': True, 'group_size': 3},
                    'consequences': {'shared_resources': True, 'cooperation_bonus': 0.2},
                    'base_enforcement': 0.6
                },
                {
                    'name': 'Fair Distribution',
                    'description': 'Resources are distributed based on need and contribution',
                    'conditions': {'resource_scarcity': True, 'group_size': 2},
                    'consequences': {'reduced_conflict': True, 'equity_bonus': 0.3},
                    'base_enforcement': 0.7
                }
            ],
            'territory': [
                {
                    'name': 'Territorial Respect',
                    'description': 'Agents respect established territories and resource claims',
                    'conditions': {'resource_competition': True, 'established_claims': True},
                    'consequences': {'reduced_conflict': True, 'territory_stability': 0.8},
                    'base_enforcement': 0.8
                },
                {
                    'name': 'Shared Territory',
                    'description': 'Agents share territory for mutual benefit',
                    'conditions': {'cooperation_level': 0.7, 'resource_abundance': True},
                    'consequences': {'increased_cooperation': True, 'resource_efficiency': 1.2},
                    'base_enforcement': 0.5
                }
            ],
            'cooperation': [
                {
                    'name': 'Mutual Aid',
                    'description': 'Agents help each other in times of need',
                    'conditions': {'agent_in_need': True, 'relationship_strength': 0.6},
                    'consequences': {'relationship_improvement': 0.3, 'reciprocity': True},
                    'base_enforcement': 0.7
                },
                {
                    'name': 'Task Specialization',
                    'description': 'Agents specialize in different tasks for efficiency',
                    'conditions': {'group_size': 4, 'skill_diversity': True},
                    'consequences': {'efficiency_bonus': 1.4, 'skill_sharing': True},
                    'base_enforcement': 0.6
                }
            ],
            'trade': [
                {
                    'name': 'Fair Exchange',
                    'description': 'Equal value exchange in trading',
                    'conditions': {'trade_frequency': 0.3, 'resource_diversity': True},
                    'consequences': {'trade_efficiency': 1.3, 'trust_building': 0.2},
                    'base_enforcement': 0.8
                },
                {
                    'name': 'Barter System',
                    'description': 'Standardized exchange rates for common goods',
                    'conditions': {'trade_sophistication': 0.5, 'resource_stability': True},
                    'consequences': {'trade_simplification': True, 'market_stability': 0.9},
                    'base_enforcement': 0.9
                }
            ]
        }
    
    def _load_recipe_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load crafting recipe templates"""
        return {
            'tools': [
                {
                    'name': 'Stone Axe',
                    'ingredients': {'stone': 2, 'wood': 1},
                    'tools_required': [],
                    'skill_required': 'tool_making',
                    'skill_level': 0.3,
                    'output': {'item': 'stone_axe', 'quantity': 1, 'durability': 50},
                    'complexity': 0.3,
                    'efficiency': 1.0
                },
                {
                    'name': 'Wooden Spear',
                    'ingredients': {'wood': 2, 'stone': 1},
                    'tools_required': ['stone_axe'],
                    'skill_required': 'weapon_making',
                    'skill_level': 0.4,
                    'output': {'item': 'wooden_spear', 'quantity': 1, 'damage': 15, 'durability': 30},
                    'complexity': 0.4,
                    'efficiency': 1.1
                }
            ],
            'buildings': [
                {
                    'name': 'Basic Shelter',
                    'ingredients': {'wood': 8, 'stone': 4},
                    'tools_required': ['stone_axe'],
                    'skill_required': 'building_basic',
                    'skill_level': 0.3,
                    'output': {'building': 'shelter', 'capacity': 2, 'protection': 0.5},
                    'complexity': 0.4,
                    'efficiency': 1.0
                },
                {
                    'name': 'Storage Hut',
                    'ingredients': {'wood': 12, 'stone': 8},
                    'tools_required': ['stone_axe', 'hammer'],
                    'skill_required': 'building_basic',
                    'skill_level': 0.5,
                    'output': {'building': 'storage', 'capacity': 20, 'protection': 0.3},
                    'complexity': 0.5,
                    'efficiency': 1.2
                }
            ],
            'food': [
                {
                    'name': 'Cooked Food',
                    'ingredients': {'raw_food': 2, 'wood': 1},
                    'tools_required': ['fire'],
                    'skill_required': 'cooking',
                    'skill_level': 0.2,
                    'output': {'item': 'cooked_food', 'quantity': 2, 'nutrition': 1.5},
                    'complexity': 0.3,
                    'efficiency': 1.3
                },
                {
                    'name': 'Preserved Food',
                    'ingredients': {'raw_food': 3, 'salt': 1},
                    'tools_required': ['storage'],
                    'skill_required': 'preservation',
                    'skill_level': 0.5,
                    'output': {'item': 'preserved_food', 'quantity': 3, 'shelf_life': 10},
                    'complexity': 0.6,
                    'efficiency': 1.5
                }
            ]
        }
    
    def evolve_rules_from_patterns(self, patterns: List[Any], turn: int) -> Dict[str, List[Any]]:
        """Evolve social rules and crafting recipes based on observed patterns"""
        new_rules = []
        new_recipes = []
        
        for pattern in patterns:
            if pattern.confidence >= 0.7 and pattern.frequency >= self.rule_threshold:
                # Generate social rule
                rule = self._create_social_rule_from_pattern(pattern, turn)
                if rule and not self._rule_exists(rule.name):
                    new_rules.append(rule)
                    self.social_rules.append(rule)
                
                # Generate crafting recipe
                recipe = self._create_crafting_recipe_from_pattern(pattern, turn)
                if recipe and not self._recipe_exists(recipe.name):
                    new_recipes.append(recipe)
                    self.crafting_recipes.append(recipe)
        
        # Record evolution
        if new_rules or new_recipes:
            self.evolution_history.append({
                'turn': turn,
                'new_rules': [rule.to_dict() for rule in new_rules],
                'new_recipes': [recipe.to_dict() for recipe in new_recipes]
            })
        
        return {
            'new_rules': new_rules,
            'new_recipes': new_recipes
        }
    
    def _create_social_rule_from_pattern(self, pattern, turn: int) -> Optional[SocialRule]:
        """Create a social rule based on a behavioral pattern"""
        category_mapping = {
            'resource_usage': 'resource_sharing',
            'social': 'cooperation',
            'collective': 'cooperation',
            'movement': 'territory',
            'individual': 'resource_sharing'
        }
        
        category = category_mapping.get(pattern.pattern_type, 'cooperation')
        templates = self.rule_templates.get(category, [])
        
        if not templates:
            return None
        
        template = templates[hash(pattern.pattern_id) % len(templates)]
        
        rule_name = self._generate_rule_name(template['name'], pattern)
        rule_id = self._generate_rule_id(rule_name, turn)
        
        return SocialRule(
            rule_id=rule_id,
            name=rule_name,
            description=self._generate_rule_description(template['description'], pattern),
            category=category,
            conditions=self._generate_rule_conditions(template['conditions'], pattern),
            consequences=self._generate_rule_consequences(template['consequences'], pattern),
            enforcement_level=template['base_enforcement'],
            adoption_rate=0.0,
            emergence_reason=f"Emerged from {pattern.pattern_type} pattern",
            based_on_pattern=pattern.pattern_id,
            generation_turn=turn
        )
    
    def _create_crafting_recipe_from_pattern(self, pattern, turn: int) -> Optional[CraftingRecipe]:
        """Create a crafting recipe based on a behavioral pattern"""
        category_mapping = {
            'resource_usage': 'tools',
            'individual': 'tools',
            'social': 'buildings',
            'collective': 'buildings',
            'movement': 'tools'
        }
        
        category = category_mapping.get(pattern.pattern_type, 'tools')
        templates = self.recipe_templates.get(category, [])
        
        if not templates:
            return None
        
        template = templates[hash(pattern.pattern_id) % len(templates)]
        
        recipe_name = self._generate_recipe_name(template['name'], pattern)
        recipe_id = self._generate_recipe_id(recipe_name, turn)
        
        return CraftingRecipe(
            recipe_id=recipe_id,
            name=recipe_name,
            description=self._generate_recipe_description(template['description'], pattern),
            ingredients=template['ingredients'],
            tools_required=template['tools_required'],
            skill_required=template['skill_required'],
            skill_level=template['skill_level'],
            output=template['output'],
            complexity=template['complexity'],
            efficiency=template['efficiency'],
            generation_reason=f"Developed from {pattern.pattern_type} pattern",
            based_on_pattern=pattern.pattern_id,
            generation_turn=turn
        )
    
    def _generate_rule_name(self, base_name: str, pattern) -> str:
        """Generate a unique rule name"""
        suffix_map = {
            'resource_usage': 'Protocol',
            'social': 'Convention',
            'collective': 'Agreement',
            'movement': 'Boundary',
            'individual': 'Guideline'
        }
        
        suffix = suffix_map.get(pattern.pattern_type, 'Rule')
        return f"{base_name} {suffix}"
    
    def _generate_recipe_name(self, base_name: str, pattern) -> str:
        """Generate a unique recipe name"""
        suffix_map = {
            'resource_usage': 'Method',
            'social': 'Collaborative',
            'collective': 'Advanced',
            'movement': 'Utility',
            'individual': 'Technique'
        }
        
        suffix = suffix_map.get(pattern.pattern_type, 'Recipe')
        return f"{base_name} {suffix}"
    
    def _generate_rule_description(self, base_description: str, pattern) -> str:
        """Generate rule description incorporating pattern insights"""
        context_additions = {
            'resource_usage': "Addressing resource management challenges",
            'social': "Facilitating social cooperation",
            'collective': "Enabling group coordination",
            'movement': "Managing spatial relationships",
            'individual': "Optimizing individual behavior"
        }
        
        addition = context_additions.get(pattern.pattern_type, "Addressing behavioral patterns")
        return f"{base_description}. {addition}."
    
    def _generate_recipe_description(self, base_description: str, pattern) -> str:
        """Generate recipe description incorporating pattern insights"""
        context_additions = {
            'resource_usage': "Optimized for efficient resource utilization",
            'social': "Designed for collaborative production",
            'collective': "Advanced technique for group benefit",
            'movement': "Practical solution for mobility needs",
            'individual': "Refined through individual practice"
        }
        
        addition = context_additions.get(pattern.pattern_type, "Developed through experience")
        return f"{base_description}. {addition}."
    
    def _generate_rule_conditions(self, base_conditions: Dict[str, Any], pattern) -> Dict[str, Any]:
        """Generate rule conditions based on pattern context"""
        conditions = base_conditions.copy()
        
        # Add pattern-specific conditions
        if pattern.pattern_type == 'resource_usage':
            conditions['resource_type'] = pattern.context.get('resource_type', 'any')
        elif pattern.pattern_type == 'social':
            conditions['group_size'] = max(conditions.get('group_size', 2), len(pattern.agents_involved))
        
        return conditions
    
    def _generate_rule_consequences(self, base_consequences: Dict[str, Any], pattern) -> Dict[str, Any]:
        """Generate rule consequences based on pattern context"""
        consequences = base_consequences.copy()
        
        # Scale consequences based on pattern confidence
        scale_factor = pattern.confidence
        for key, value in consequences.items():
            if isinstance(value, (int, float)):
                consequences[key] = value * scale_factor
        
        return consequences
    
    def _generate_rule_id(self, rule_name: str, turn: int) -> str:
        """Generate a unique rule ID"""
        content = f"{rule_name}_{turn}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def _generate_recipe_id(self, recipe_name: str, turn: int) -> str:
        """Generate a unique recipe ID"""
        content = f"{recipe_name}_{turn}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def _rule_exists(self, rule_name: str) -> bool:
        """Check if a rule with this name already exists"""
        return any(rule.name == rule_name for rule in self.social_rules)
    
    def _recipe_exists(self, recipe_name: str) -> bool:
        """Check if a recipe with this name already exists"""
        return any(recipe.name == recipe_name for recipe in self.crafting_recipes)
    
    def get_available_rules(self, agent_id: str, agent_context: Dict[str, Any]) -> List[SocialRule]:
        """Get social rules relevant to an agent's context"""
        relevant_rules = []
        
        for rule in self.social_rules:
            if self._rule_applies_to_context(rule, agent_context):
                relevant_rules.append(rule)
        
        return relevant_rules
    
    def get_available_recipes(self, agent_skills: Dict[str, float], 
                            agent_inventory: Dict[str, float]) -> List[CraftingRecipe]:
        """Get crafting recipes available to an agent"""
        available_recipes = []
        
        for recipe in self.crafting_recipes:
            if self._can_craft_recipe(recipe, agent_skills, agent_inventory):
                available_recipes.append(recipe)
        
        return available_recipes
    
    def _rule_applies_to_context(self, rule: SocialRule, agent_context: Dict[str, Any]) -> bool:
        """Check if a rule applies to the given agent context"""
        conditions = rule.conditions
        
        for condition_key, condition_value in conditions.items():
            if condition_key in agent_context:
                context_value = agent_context[condition_key]
                if isinstance(condition_value, (int, float)):
                    if context_value < condition_value:
                        return False
                elif context_value != condition_value:
                    return False
        
        return True
    
    def _can_craft_recipe(self, recipe: CraftingRecipe, 
                         agent_skills: Dict[str, float], 
                         agent_inventory: Dict[str, float]) -> bool:
        """Check if an agent can craft a recipe"""
        # Check skill requirement
        if agent_skills.get(recipe.skill_required, 0) < recipe.skill_level:
            return False
        
        # Check ingredients
        for ingredient, required_amount in recipe.ingredients.items():
            if agent_inventory.get(ingredient, 0) < required_amount:
                return False
        
        # Check tools (simplified - assume basic tools are available)
        return True
    
    def update_rule_adoption(self, rule_id: str, adoption_rate: float):
        """Update the adoption rate of a social rule"""
        for rule in self.social_rules:
            if rule.rule_id == rule_id:
                rule.adoption_rate = max(0.0, min(1.0, adoption_rate))
                break
    
    def get_evolution_summary(self) -> Dict[str, Any]:
        """Get summary of rule and recipe evolution"""
        rule_categories = {}
        for rule in self.social_rules:
            rule_categories[rule.category] = rule_categories.get(rule.category, 0) + 1
        
        recipe_categories = {}
        for recipe in self.crafting_recipes:
            recipe_type = recipe.output.get('item', 'building')
            recipe_categories[recipe_type] = recipe_categories.get(recipe_type, 0) + 1
        
        return {
            'total_rules': len(self.social_rules),
            'rules_by_category': rule_categories,
            'total_recipes': len(self.crafting_recipes),
            'recipes_by_type': recipe_categories,
            'evolution_history': self.evolution_history[-10:],
            'all_rules': [rule.to_dict() for rule in self.social_rules],
            'all_recipes': [recipe.to_dict() for recipe in self.crafting_recipes]
        }
    
    def reset_rules(self):
        """Reset all rules and recipes (for testing purposes)"""
        self.social_rules.clear()
        self.crafting_recipes.clear()
        self.evolution_history.clear()