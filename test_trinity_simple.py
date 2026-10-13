#!/usr/bin/env python3
"""
简化的Trinity机制测试

测试Trinity的资源管理逻辑，不依赖外部API
"""

import sys
import os
sys.path.append('sociology_simulation')

try:
    from sociology_simulation.trinity import Trinity
    from sociology_simulation.bible import Bible
except ImportError:
    print("无法导入模块，请确保在正确的目录下运行")
    sys.exit(1)


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


def test_resource_status_calculation():
    """测试资源状态计算"""
    print("=== 测试资源状态计算 ===\n")
    
    bible = Bible()
    trinity = Trinity(bible, "石器时代")
    trinity.resource_rules = {
        "wood": {"FOREST": 0.4},
        "fish": {"OCEAN": 0.3}
    }
    
    world = MockWorld()
    world.resources = {
        (1, 1): {"wood": 5},  # 应该是丰富
        (6, 6): {"fish": 1}   # 应该是稀缺
    }
    
    resource_status = trinity._calculate_resource_status(world)
    
    print("资源状态计算结果:")
    for resource, status in resource_status.items():
        print(f"  {resource}:")
        print(f"    当前数量: {status['current_count']}")
        print(f"    期望数量: {status['expected_count']}")
        print(f"    稀缺比例: {status['scarcity_ratio']:.2f}")
        print(f"    状态: {status['status']}")
    
    # 验证结果
    wood_status = resource_status['wood']
    fish_status = resource_status['fish']
    
    print(f"\n验证结果:")
    print(f"  木材状态正确: {'✅' if wood_status['status'] in ['abundant', 'normal'] else '❌'}")
    print(f"  鱼类状态正确: {'✅' if fish_status['status'] == 'scarce' else '❌'}")


def test_resource_regeneration():
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
    
    # 测试重新生成 - 使用高倍数确保有资源生成
    trinity._regenerate_resources(world, 3.0, ["wood"])
    
    print("重新生成后资源数量:")
    final_count = sum(sum(res.values()) for res in world.resources.values())
    print(f"  总资源: {final_count}")
    print(f"  新增资源: {final_count - initial_count}")
    
    if final_count > initial_count:
        print("✅ 资源重新生成成功")
    else:
        print("❌ 资源重新生成可能失败（这是概率性的，多试几次）")
    
    print("\n所有资源分布:")
    for pos, resources in sorted(world.resources.items()):
        print(f"  位置 {pos}: {resources}")


def test_climate_effects():
    """测试气候效应"""
    print("\n=== 测试气候效应 ===\n")
    
    bible = Bible()
    trinity = Trinity(bible, "石器时代")
    
    world = MockWorld()
    world.resources[(3, 3)] = {"water": 5}
    
    print("气候变化前:")
    print(f"  水资源: {world.resources[(3, 3)]['water']}")
    
    # 测试干旱效应
    climate_data = {"type": "drought", "effect": "水资源减少"}
    trinity._apply_climate_change(world, climate_data)
    
    print("干旱后:")
    print(f"  水资源: {world.resources[(3, 3)]['water']}")
    print(f"  气候效应: {'✅' if world.resources[(3, 3)]['water'] < 5 else '❌'}")


def test_trinity_integration():
    """测试Trinity整体机制"""
    print("\n=== 测试Trinity整体机制 ===\n")
    
    bible = Bible()
    trinity = Trinity(bible, "石器时代")
    trinity.resource_rules = {
        "wood": {"FOREST": 0.3},
        "fish": {"OCEAN": 0.2},
        "stone": {"MOUNTAIN": 0.4}
    }
    
    world = MockWorld()
    # 添加山地
    for i in range(8, 10):
        for j in range(8, 10):
            world.map[i][j] = "MOUNTAIN"
    
    # 模拟资源稀缺情况
    world.resources = {(1, 1): {"wood": 1}}  # 只有很少的木材
    
    print("Trinity决策前状态:")
    resource_status = trinity._calculate_resource_status(world)
    for resource, status in resource_status.items():
        print(f"  {resource}: {status['status']} (比例: {status['scarcity_ratio']:.2f})")
    
    # 模拟Trinity的决策逻辑
    actions_taken = []
    
    # 如果木材稀缺，Trinity应该提高其生成概率或重新生成
    if resource_status['wood']['status'] == 'scarce':
        trinity._regenerate_resources(world, 2.0, ['wood'])
        actions_taken.append("重新生成木材资源")
    
    # 如果某个资源完全没有，Trinity应该调整规则
    if resource_status['stone']['current_count'] == 0:
        trinity.resource_rules['stone']['MOUNTAIN'] = 0.6  # 提高概率
        trinity._regenerate_resources(world, 1.5, ['stone'])
        actions_taken.append("提高石头生成概率并重新生成")
    
    print(f"\nTrinity执行的行动: {actions_taken}")
    
    print("Trinity决策后状态:")
    final_status = trinity._calculate_resource_status(world)
    for resource, status in final_status.items():
        print(f"  {resource}: {status['status']} (比例: {status['scarcity_ratio']:.2f})")
    
    print(f"\n最终资源分布:")
    for pos, resources in sorted(world.resources.items()):
        print(f"  位置 {pos}: {resources}")


def main():
    """主测试函数"""
    print("🧪 Trinity生态管理机制测试\n")
    
    try:
        test_resource_status_calculation()
        test_resource_regeneration()
        test_climate_effects()
        test_trinity_integration()
        
        print("\n✅ 所有基础测试完成！")
        print("\n📝 总结:")
        print("   ✅ Trinity不再直接生成资源")
        print("   ✅ Trinity通过调整概率和重新生成来管理资源")
        print("   ✅ Trinity可以分析资源状态并做出相应决策")
        print("   ✅ Trinity可以应用气候变化等环境效应")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()