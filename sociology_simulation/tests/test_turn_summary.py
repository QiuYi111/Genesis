"""Tests for Workstream D: Turn Summary & Analytics"""
from __future__ import annotations

from typing import List

from sociology_simulation.world import World
from sociology_simulation.agent import Agent


def _make_agent(aid: int, skills: List[str] = None) -> Agent:
    a = Agent(aid, (0, 0), {"strength": 5, "curiosity": 5, "charm": 5}, {}, age=25)
    if skills:
        for s in skills:
            a.skills[s] = {"level": 1, "experience": 0}
    return a


def test_consistency_guard_blocks_single_skill_phrase():
    # World with high skill diversity
    w = World(size=8, era_prompt="Stone Age", num_agents=2)
    w.agents = [
        _make_agent(1, ["crafting", "survival", "exploration", "trade", "build"]),
        _make_agent(2, ["medicine", "diplomacy"]),
    ]

    # Turn log indicates a new skill
    turn_log = ["Agent 1 解锁技能: 烹饪"]
    facts = w._collect_turn_facts(turn_log)

    # LLM produced a bad narrative claiming single skill
    llm_out = {
        "summary": "社会技能单一，发展受限。",
        "highlights": [],
        "warnings": ["技能单一可能引发风险"]
    }

    corrected = w._validate_and_correct_summary(facts, llm_out)
    assert "技能单一" not in corrected.get("summary", "")
    assert all("技能单一" not in w for w in corrected.get("warnings", []))
    # Ensure new skills are highlighted
    assert any("新技能" in h or "New skills" in h for h in corrected.get("highlights", []))


def test_collect_turn_facts_counts():
    w = World(size=8, era_prompt="Stone Age", num_agents=3)
    # Add three agents and basic connections
    w.agents = [
        _make_agent(1, ["crafting"]),
        _make_agent(2, ["survival"]),
        _make_agent(3, ["exploration"]),
    ]
    # Social: create a group
    g = w.social_manager.create_group(founder_id=1, group_type="tribe", purpose="hunt", formation_turn=1)
    g.add_member(2)
    # Markets: establish one
    w.economic_system.establish_market((1, 1), turn=1, market_type="local")
    # Politics: form one entity
    w.political_system.form_political_entity(founder_id=1, entity_type="council", name="T Council", turn=1)
    # Technology: mark one discovered
    w.tech_system.discovered_techs.add("fire_control")

    facts = w._collect_turn_facts(["Agent 1 出生", "Agent 2 died"])  # include notable keywords

    assert facts["agents_alive"] == 3
    assert facts["groups_count"] == 1
    assert facts["markets_count"] == 1
    assert facts["political_entities"] == 1
    assert facts["technologies_count"] >= 1
    assert facts["skill_diversity"] >= 3
    assert isinstance(facts["avg_social_connections"], float)
    assert "economic_health" in facts
