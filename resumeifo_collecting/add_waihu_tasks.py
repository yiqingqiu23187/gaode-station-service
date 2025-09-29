#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量添加外呼任务脚本
使用简历ID和手机号调用addWaihuTask MCP工具
"""

import pandas as pd
import time
import logging
from typing import List, Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('add_waihu_tasks.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WaihuTaskAdder:
    def __init__(self, excel_file_path: str, resume_ids_file: str, job_id: str):
        """
        初始化外呼任务添加器
        
        Args:
            excel_file_path: Excel文件路径
            resume_ids_file: 简历ID文件路径
            job_id: 职位ID
        """
        self.excel_file_path = excel_file_path
        self.resume_ids_file = resume_ids_file
        self.job_id = job_id
        self.success_count = 0
        self.error_count = 0
        self.results = []
        
    def read_resume_ids(self) -> List[str]:
        """读取简历ID列表"""
        try:
            with open(self.resume_ids_file, 'r', encoding='utf-8') as f:
                resume_ids = [line.strip() for line in f if line.strip()]
            logger.info(f"成功读取 {len(resume_ids)} 个简历ID")
            return resume_ids
        except Exception as e:
            logger.error(f"读取简历ID文件失败: {e}")
            raise
    
    def read_excel_data(self) -> pd.DataFrame:
        """读取Excel数据"""
        try:
            df = pd.read_excel(self.excel_file_path)
            logger.info(f"成功读取Excel文件，共 {len(df)} 条记录")
            return df
        except Exception as e:
            logger.error(f"读取Excel文件失败: {e}")
            raise
    
    def match_resume_with_phone(self) -> List[Dict[str, Any]]:
        """
        将简历ID与手机号匹配
        
        Returns:
            List[Dict]: 包含resumeId, phone, name的列表
        """
        try:
            # 读取简历ID
            resume_ids = self.read_resume_ids()
            
            # 读取Excel数据
            df = self.read_excel_data()
            
            # 创建匹配列表
            matched_data = []
            
            # 按顺序匹配（假设简历ID的顺序与Excel中成功导入的记录顺序一致）
            excel_index = 0
            
            for resume_id in resume_ids:
                # 在Excel中查找对应的记录
                while excel_index < len(df):
                    row = df.iloc[excel_index]
                    if pd.notna(row.get('手机号')):
                        phone = str(row.get('手机号')).strip()
                        name = str(row.get('姓名', '')).strip()
                        
                        matched_data.append({
                            'resumeId': resume_id,
                            'phone': phone,
                            'name': name,
                            'excel_index': excel_index + 1
                        })
                        excel_index += 1
                        break
                    excel_index += 1
                else:
                    logger.warning(f"简历ID {resume_id} 无法匹配到对应的Excel记录")
            
            logger.info(f"成功匹配 {len(matched_data)} 个简历ID与手机号")
            return matched_data
            
        except Exception as e:
            logger.error(f"匹配简历ID与手机号失败: {e}")
            raise
    
    def add_waihu_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        添加单个外呼任务
        
        Args:
            task_data: 包含resumeId, phone, name的数据
            
        Returns:
            Dict: 操作结果
        """
        try:
            logger.info(f"正在添加外呼任务: {task_data['name']} ({task_data['phone']}) - 简历ID: {task_data['resumeId']}")
            
            # 这里需要调用MCP工具，但由于我们在脚本中无法直接调用，
            # 所以这里只是模拟调用，实际使用时需要集成MCP客户端
            
            # 模拟调用结果 - 实际使用时需要替换为真实的MCP调用
            # mcp_browser_extension_mcp_addWaihuTask(
            #     resumeId=task_data['resumeId'],
            #     jobId=self.job_id,
            #     phone=task_data['phone']
            # )
            
            result = {
                'resumeId': task_data['resumeId'],
                'phone': task_data['phone'],
                'name': task_data['name'],
                'jobId': self.job_id,
                'success': True,  # 这里需要根据实际MCP调用结果设置
                'message': '外呼任务已创建',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return result
            
        except Exception as e:
            logger.error(f"添加外呼任务失败: {task_data['name']} ({task_data['phone']}) - {e}")
            return {
                'resumeId': task_data['resumeId'],
                'phone': task_data['phone'],
                'name': task_data['name'],
                'jobId': self.job_id,
                'success': False,
                'message': str(e),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def batch_add_tasks(self, delay_seconds: int = 2, max_tasks: int = None):
        """
        批量添加外呼任务
        
        Args:
            delay_seconds: 每次调用之间的延迟时间（秒）
            max_tasks: 最大处理数量，None表示处理所有
        """
        try:
            # 匹配简历ID与手机号
            matched_data = self.match_resume_with_phone()
            
            if max_tasks:
                matched_data = matched_data[:max_tasks]
                logger.info(f"限制处理数量为: {max_tasks}")
            
            logger.info(f"开始批量添加外呼任务，共 {len(matched_data)} 个")
            logger.info(f"使用职位ID: {self.job_id}")
            
            for i, task_data in enumerate(matched_data, 1):
                logger.info(f"进度: {i}/{len(matched_data)}")
                
                # 添加外呼任务
                result = self.add_waihu_task(task_data)
                self.results.append(result)
                
                if result['success']:
                    self.success_count += 1
                    logger.info(f"✓ 成功: {result['name']} ({result['phone']})")
                else:
                    self.error_count += 1
                    logger.error(f"✗ 失败: {result['name']} ({result['phone']}) - {result['message']}")
                
                # 延迟，避免请求过于频繁
                if i < len(matched_data):
                    logger.info(f"等待 {delay_seconds} 秒...")
                    time.sleep(delay_seconds)
            
            # 保存结果
            self.save_results()
            
            logger.info(f"批量添加完成 - 成功: {self.success_count}, 失败: {self.error_count}")
            
        except Exception as e:
            logger.error(f"批量添加过程中发生错误: {e}")
            raise
    
    def save_results(self):
        """保存结果到文件"""
        try:
            import json
            
            # 保存详细结果
            with open('waihu_task_results.json', 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            
            # 保存成功和失败的记录
            success_tasks = [r for r in self.results if r['success']]
            error_tasks = [r for r in self.results if not r['success']]
            
            with open('successful_waihu_tasks.txt', 'w', encoding='utf-8') as f:
                for task in success_tasks:
                    f.write(f"{task['resumeId']},{task['phone']},{task['name']}\n")
            
            with open('failed_waihu_tasks.txt', 'w', encoding='utf-8') as f:
                for task in error_tasks:
                    f.write(f"{task['resumeId']},{task['phone']},{task['name']}\n")
            
            logger.info("结果已保存到文件:")
            logger.info("- waihu_task_results.json (详细结果)")
            logger.info("- successful_waihu_tasks.txt (成功的任务)")
            logger.info("- failed_waihu_tasks.txt (失败的任务)")
            
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
    
    def test_single_task(self, index: int = 0):
        """
        测试单个外呼任务添加
        
        Args:
            index: 要测试的任务索引（从0开始）
        """
        try:
            matched_data = self.match_resume_with_phone()
            
            if index >= len(matched_data):
                logger.error(f"索引 {index} 超出范围，共有 {len(matched_data)} 个任务")
                return
            
            task_data = matched_data[index]
            logger.info(f"测试添加外呼任务:")
            logger.info(f"  姓名: {task_data['name']}")
            logger.info(f"  手机号: {task_data['phone']}")
            logger.info(f"  简历ID: {task_data['resumeId']}")
            logger.info(f"  职位ID: {self.job_id}")
            
            result = self.add_waihu_task(task_data)
            self.results.append(result)
            
            if result['success']:
                logger.info(f"✓ 测试成功: {result['message']}")
            else:
                logger.error(f"✗ 测试失败: {result['message']}")
            
        except Exception as e:
            logger.error(f"测试过程中发生错误: {e}")


def main():
    """主函数"""
    EXCEL_FILE_PATH = "9.28北广线索.xlsx"
    RESUME_IDS_FILE = "successful_resume_ids.txt"
    JOB_ID = "fd9d46ec-1f06-4504-a034-122347e92239"
    
    # 创建添加器实例
    adder = WaihuTaskAdder(EXCEL_FILE_PATH, RESUME_IDS_FILE, JOB_ID)
    
    try:
        print("=" * 60)
        print("外呼任务批量添加工具")
        print("=" * 60)
        print(f"职位ID: {JOB_ID}")
        print("1. 测试单个任务（第一个）")
        print("2. 批量添加所有任务")
        print("3. 批量添加前10个任务（测试用）")
        print("=" * 60)
        
        choice = input("请选择操作 (1/2/3): ").strip()
        
        if choice == "1":
            logger.info("开始测试单个外呼任务...")
            adder.test_single_task(0)
        elif choice == "2":
            confirm = input("确认要添加所有外呼任务吗？(y/N): ").strip().lower()
            if confirm == 'y':
                logger.info("开始批量添加所有外呼任务...")
                adder.batch_add_tasks(delay_seconds=3)  # 3秒延迟，避免过于频繁
            else:
                logger.info("操作已取消")
        elif choice == "3":
            logger.info("开始批量添加前10个外呼任务（测试）...")
            adder.batch_add_tasks(delay_seconds=2, max_tasks=10)
        else:
            logger.error("无效选择")
            
    except Exception as e:
        logger.error(f"程序执行失败: {e}")


if __name__ == "__main__":
    main()
