#!/usr/bin/env python3
"""
测试Trinity改进机制

验证Trinity不再直接生成资源，而是通过生态管理来影响世界
"""

import asyncio
import aiohttp
import sys
import os
sys.path.append('sociology_simulation')

from sociology_simulation.trinity import Trinity
from sociology_simulation.bible import Bible
from sociology_simulation.world import World
from sociology_simulation.prompts import init_prompt_manager
from sociology_simulation.enhanced_llm import init_llm_service
from sociology_simulation.config import init_llm_service as init_config


class MockWorld:
    """Mock world for testing"""
    def __init__(self):
        self.size = 10
        self.agents = []
        self.map = [["FOREST" if i < 5 else "OCEAN" for j in range(10)] for i in range(10)]
        self.resources = {
            (1, 1): {"wood": 3},
            (2, 2): {"wood": 1}, 
            (6, 6): {"fish": 2}
        }


async def test_trinity_ecological_management():
    """测试Trinity的生态管理功能"""
    print("=== 测试Trinity生态管理机制 ===\n")
    
    # 初始化系统
    prompt_manager = init_prompt_manager()
    llm_service = init_llm_service(prompt_manager)
    
    # 创建Trinity实例
    bible = Bible()
    trinity = Trinity(bible, "石器时代")
    trinity.resource_rules = {
        "wood": {"FOREST": 0.3},
        "fish": {"OCEAN": 0.2}
    }
    
    # 创建模拟世界
    world = MockWorld()
    
    print("初始资源状态:")
    for pos, resources in world.resources.items():
        print(f"  位置 {pos}: {resources}")
    
    print(f"\n当前资源规则: {trinity.resource_rules}")
    
    # 计算资源状态
    resource_status = trinity._calculate_resource_status(world)
    print(f"\n资源状态分析:")
    for resource, status in resource_status.items():
        print(f"  {resource}: {status}")
    
    async with aiohttp.ClientSession() as session:
        # 测试Trinity的行动决策
        print(f"\n=== Trinity决策测试 ===")
        try:
            await trinity.execute_actions(world, session)
            print("✅ Trinity生态管理执行成功")
        except Exception as e:
            print(f"❌ Trinity执行失败: {e}")
    
    print(f"\n执行后资源规则: {trinity.resource_rules}")
    
    print("\n执行后资源状态:")
    for pos, resources in world.resources.items():
        print(f"  位置 {pos}: {resources}")


async def test_resource_regeneration():
    """测试资源重新生成机制"""
    print("\n=== 测试资源重新生成机制 ===\n")
    
    bible = Bible()
    trinity = Trinity(bible, "石器时代") 
    trinity.resource_rules = {
        "wood": {"FOREST": 0.5},
        "stone": {"MOUNTAIN": 0.3}
    }
    
    world = MockWorld()
    # 添加山地地形
    for i in range(7, 10):
        for j in range(7, 10):
            world.map[i][j] = "MOUNTAIN"
    
    print("重新生成前资源数量:")
    initial_count = sum(sum(res.values()) for res in world.resources.values())
    print(f"  总资源: {initial_count}")
    
    # 测试重新生成
    trinity._regenerate_resources(world, 2.0, ["wood"])
    
    print("重新生成后资源数量:")
    final_count = sum(sum(res.values()) for res in world.resources.values())
    print(f"  总资源: {final_count}")
    print(f"  新增资源: {final_count - initial_count}")
    
    print("\n新的资源分布:")
    for pos, resources in world.resources.items():
        if pos not in [(1, 1), (2, 2), (6, 6)]:  # 只显示新生成的
            print(f"  位置 {pos}: {resources}")


def test_resource_status_calculation():
    """测试资源状态计算"""
    print("\n=== 测试资源状态计算 ===\n")
    
    bible = Bible()
    trinity = Trinity(bible, "石器时代")
    trinity.resource_rules = {
        "wood": {"FOREST": 0.4},
        "fish": {"OCEAN": 0.3}
    }
    
    world = MockWorld()
    world.resources = {
        (1, 1): {"wood": 5},  # 丰富
        (6, 6): {"fish": 1}   # 稀缺
    }
    
    resource_status = trinity._calculate_resource_status(world)
    
    print("资源状态计算结果:")
    for resource, status in resource_status.items():
        print(f"  {resource}:")
        print(f"    当前数量: {status['current_count']}")
        print(f"    期望数量: {status['expected_count']}")
        print(f"    稀缺比例: {status['scarcity_ratio']:.2f}")
        print(f"    状态: {status['status']}")


async def main():
    """主测试函数"""
    print("🧪 Trinity生态管理机制测试\n")
    
    try:
        # 测试基本功能
        test_resource_status_calculation()
        await test_resource_regeneration()
        
        # 测试完整的生态管理（需要API）
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            await test_trinity_ecological_management()
        else:
            print("⚠️  未设置DEEPSEEK_API_KEY，跳过LLM相关测试")
        
        print("\n✅ 所有测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())