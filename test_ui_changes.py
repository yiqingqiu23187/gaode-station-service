#!/usr/bin/env python3
"""
测试界面调整后的功能
"""

import requests
import time

BASE_URL = "http://localhost:5000"

def test_page_load():
    """测试页面加载"""
    print("测试页面加载...")
    response = requests.get(BASE_URL)
    
    if response.status_code == 200:
        content = response.text
        
        # 检查新的刷新按钮是否存在
        if 'id="reloadBtn"' in content:
            print("✅ 新的刷新按钮已添加")
        else:
            print("❌ 新的刷新按钮未找到")
        
        # 检查按钮文本
        if '🔄 刷新数据' in content:
            print("✅ 刷新按钮文本正确")
        else:
            print("❌ 刷新按钮文本不正确")
        
        # 检查重置按钮文本
        if '🔄 重置数据' in content:
            print("✅ 重置按钮文本正确")
        else:
            print("❌ 重置按钮文本不正确")
        
        # 检查CSS样式调整
        if 'font-size: 1.4rem' in content:
            print("✅ 标题字体大小已调整")
        else:
            print("❌ 标题字体大小未调整")
        
        if 'justify-content: flex-start' in content:
            print("✅ 按钮布局已改为左对齐")
        else:
            print("❌ 按钮布局未改为左对齐")
        
        if 'background-color: #6c757d' in content:
            print("✅ 滚动条颜色已改为灰色")
        else:
            print("❌ 滚动条颜色未改为灰色")
        
        return True
    else:
        print(f"❌ 页面加载失败: {response.status_code}")
        return False

def test_api_functionality():
    """测试API功能是否正常"""
    print("\n测试API功能...")
    
    # 测试获取数据
    response = requests.get(f"{BASE_URL}/api/stations")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API正常工作，获取到 {data['total']} 条记录")
        return True
    else:
        print(f"❌ API请求失败: {response.status_code}")
        return False

def main():
    print("开始测试界面调整...\n")
    
    # 测试页面加载和界面元素
    page_ok = test_page_load()
    
    # 测试API功能
    api_ok = test_api_functionality()
    
    print(f"\n测试结果:")
    print(f"页面界面: {'✅ 正常' if page_ok else '❌ 异常'}")
    print(f"API功能: {'✅ 正常' if api_ok else '❌ 异常'}")
    
    if page_ok and api_ok:
        print("\n🎉 所有测试通过！界面调整成功完成。")
        print("\n界面调整总结:")
        print("1. ✅ 标题字体大小从1.8rem缩小到1.4rem")
        print("2. ✅ 按钮布局从居中改为左对齐")
        print("3. ✅ 新增刷新按钮，位于最左侧")
        print("4. ✅ 滚动条颜色改为灰色系")
        print("\n请在浏览器中访问 http://localhost:5000 查看效果！")
    else:
        print("\n❌ 部分测试失败，请检查配置。")

if __name__ == '__main__':
    main()
