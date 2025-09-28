#!/usr/bin/env python3
"""
测试 interview_information 工具的脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入mcp_server模块
from mcp_server import interview_information, get_job_by_id

def test_interview_information():
    """测试 interview_information 函数"""
    print("=== 测试 interview_information 工具 ===")
    
    # 测试用例1：使用有效的job_id
    print("\n1. 测试有效的job_id (ID=1):")
    result1 = interview_information(job_id=1)
    print(f"结果: {result1}")
    
    # 测试用例2：使用有效的job_id，带用户坐标（虽然不会被使用）
    print("\n2. 测试有效的job_id (ID=2) 带用户坐标:")
    result2 = interview_information(job_id=2, user_latitude=23.1291, user_longitude=113.2644)
    print(f"结果: {result2}")
    
    # 测试用例3：使用无效的job_id
    print("\n3. 测试无效的job_id (ID=99999):")
    result3 = interview_information(job_id=99999)
    print(f"结果: {result3}")
    
    # 对比测试：使用相同的job_id调用get_job_by_id，看看输出的差异
    print("\n=== 对比测试：get_job_by_id vs interview_information ===")
    print("\nget_job_by_id(job_id=1) 的结果:")
    full_result = get_job_by_id(job_id=1)
    print(f"完整信息: {full_result}")
    
    print("\ninterview_information(job_id=1) 的结果:")
    interview_result = interview_information(job_id=1)
    print(f"面试信息: {interview_result}")
    
    # 验证输出格式
    print("\n=== 验证输出格式 ===")
    if interview_result and not interview_result[0].get('error'):
        info = interview_result[0]
        expected_keys = {'recruiting_unit', 'interview_time'}
        actual_keys = set(info.keys())
        
        print(f"期望的字段: {expected_keys}")
        print(f"实际的字段: {actual_keys}")
        print(f"字段匹配: {expected_keys == actual_keys}")
        
        if expected_keys == actual_keys:
            print("✅ 输出格式正确！")
        else:
            print("❌ 输出格式不匹配！")
    else:
        print("❌ 获取面试信息失败！")

if __name__ == "__main__":
    test_interview_information()
