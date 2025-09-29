#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量添加微信联系人脚本
从Excel文件读取手机号，调用MCP工具添加微信联系人
"""

import pandas as pd
import time
import logging
import asyncio
import json
from typing import List, Dict, Any, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('add_wechat_contacts.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WechatContactAdder:
    def __init__(self, excel_file_path: str):
        """
        初始化微信联系人添加器
        
        Args:
            excel_file_path: Excel文件路径
        """
        self.excel_file_path = excel_file_path
        self.success_count = 0
        self.error_count = 0
        self.results = []
        
        # MCP相关属性
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._streams_context = None
        self._session_context = None

        # MCP服务器配置
        self.mcp_config = {
            "url": "http://152.136.8.68:3001/mcp",
            "headers": {},
            "timeout": 50
        }

    async def connect_to_mcp_server(self):
        """连接到MCP服务器"""
        try:
            logger.info(f"正在连接到MCP服务器: {self.mcp_config['url']}")

            self._streams_context = streamablehttp_client(
                url=self.mcp_config['url'],
                headers=self.mcp_config['headers'],
            )
            read_stream, write_stream, _ = await self._streams_context.__aenter__()

            self._session_context = ClientSession(read_stream, write_stream)
            self.session = await self._session_context.__aenter__()

            await self.session.initialize()
            logger.info("成功连接到MCP服务器")

            # 列出可用工具
            response = await self.session.list_tools()
            available_tools = [tool.name for tool in response.tools]
            logger.info(f"可用工具: {', '.join(available_tools)}")

        except Exception as e:
            logger.error(f"连接MCP服务器失败: {e}")
            raise

    async def disconnect_from_mcp_server(self):
        """断开MCP服务器连接"""
        try:
            if self._session_context:
                await self._session_context.__aexit__(None, None, None)
            if self._streams_context:
                await self._streams_context.__aexit__(None, None, None)
            logger.info("已断开MCP服务器连接")
        except Exception as e:
            logger.error(f"断开MCP服务器连接时发生错误: {e}")

    def read_phone_numbers(self) -> List[Dict[str, Any]]:
        """
        从Excel文件读取手机号
        
        Returns:
            List[Dict]: 包含姓名和手机号的列表
        """
        try:
            df = pd.read_excel(self.excel_file_path)
            phone_data = []
            
            for index, row in df.iterrows():
                if pd.notna(row.get('手机号')):
                    phone_data.append({
                        'index': index + 1,
                        'name': str(row.get('姓名', '')).strip(),
                        'phone': str(row.get('手机号')).strip()
                    })
            
            logger.info(f"成功读取 {len(phone_data)} 个有效手机号")
            return phone_data
            
        except Exception as e:
            logger.error(f"读取Excel文件失败: {e}")
            raise
    
    async def add_contact(self, phone_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        添加单个联系人
        
        Args:
            phone_data: 包含姓名和手机号的数据
            
        Returns:
            Dict: 操作结果
        """
        try:
            if not self.session:
                raise Exception("MCP会话未初始化，请先连接到服务器")
            
            logger.info(f"正在添加联系人: {phone_data['name']} ({phone_data['phone']})")
            
            # 调用MCP工具创建添加联系人任务
            tool_args = {
                "phoneNumber": phone_data['phone'],
                "name": phone_data['name']
            }

            # 调用createAddContactTask工具
            result = await self.session.call_tool("createAddContactTask", tool_args)

            # 解析MCP调用结果
            if result.isError:
                error_message = f"MCP调用失败: {result.content}"
                logger.error(error_message)
                return {
                    'index': phone_data['index'],
                    'name': phone_data['name'],
                    'phone': phone_data['phone'],
                    'success': False,
                    'message': error_message,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }

            # 成功的情况
            success_message = f"任务已创建: {result.content}"
            logger.info(f"✓ MCP调用成功: {success_message}")

            return {
                'index': phone_data['index'],
                'name': phone_data['name'],
                'phone': phone_data['phone'],
                'success': True,
                'message': success_message,
                'mcp_result': result.content,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            error_message = f"添加联系人失败: {str(e)}"
            logger.error(f"添加联系人失败: {phone_data['name']} ({phone_data['phone']}) - {e}")
            return {
                'index': phone_data['index'],
                'name': phone_data['name'],
                'phone': phone_data['phone'],
                'success': False,
                'message': error_message,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
    
    async def batch_add_contacts(self, delay_seconds: int = 2, max_contacts: int = None):
        """
        批量添加联系人
        
        Args:
            delay_seconds: 每次调用之间的延迟时间（秒）
            max_contacts: 最大处理数量，None表示处理所有
        """
        try:
            # 连接到MCP服务器
            await self.connect_to_mcp_server()

            # 读取手机号
            phone_data_list = self.read_phone_numbers()
            
            if max_contacts:
                phone_data_list = phone_data_list[:max_contacts]
                logger.info(f"限制处理数量为: {max_contacts}")
            
            logger.info(f"开始批量添加联系人，共 {len(phone_data_list)} 个")
            
            for i, phone_data in enumerate(phone_data_list, 1):
                logger.info(f"进度: {i}/{len(phone_data_list)}")
                
                # 添加联系人
                result = await self.add_contact(phone_data)
                self.results.append(result)
                
                if result['success']:
                    self.success_count += 1
                    logger.info(f"✓ 成功: {result['name']} ({result['phone']})")
                else:
                    self.error_count += 1
                    logger.error(f"✗ 失败: {result['name']} ({result['phone']}) - {result['message']}")
                
                # 延迟，避免请求过于频繁
                if i < len(phone_data_list):
                    logger.info(f"等待 {delay_seconds} 秒...")
                    await asyncio.sleep(delay_seconds)
            
            # 保存结果
            self.save_results()
            
            logger.info(f"批量添加完成 - 成功: {self.success_count}, 失败: {self.error_count}")
            
        except Exception as e:
            logger.error(f"批量添加过程中发生错误: {e}")
            raise
        finally:
            # 断开MCP服务器连接
            await self.disconnect_from_mcp_server()
    
    def save_results(self):
        """保存结果到文件"""
        try:
            # 保存详细结果
            with open('wechat_contact_results.json', 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            
            # 保存成功和失败的手机号
            success_phones = [r['phone'] for r in self.results if r['success']]
            error_phones = [r['phone'] for r in self.results if not r['success']]
            
            with open('successful_phones.txt', 'w', encoding='utf-8') as f:
                for phone in success_phones:
                    f.write(f"{phone}\n")
            
            with open('failed_phones.txt', 'w', encoding='utf-8') as f:
                for phone in error_phones:
                    f.write(f"{phone}\n")
            
            logger.info("结果已保存到文件:")
            logger.info("- wechat_contact_results.json (详细结果)")
            logger.info("- successful_phones.txt (成功的手机号)")
            logger.info("- failed_phones.txt (失败的手机号)")
            
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
    
    async def test_single_contact(self, index: int = 0):
        """
        测试单个联系人添加
        
        Args:
            index: 要测试的联系人索引（从0开始）
        """
        try:
            # 连接到MCP服务器
            await self.connect_to_mcp_server()

            phone_data_list = self.read_phone_numbers()
            
            if index >= len(phone_data_list):
                logger.error(f"索引 {index} 超出范围，共有 {len(phone_data_list)} 个联系人")
                return
            
            phone_data = phone_data_list[index]
            logger.info(f"测试添加联系人: {phone_data['name']} ({phone_data['phone']})")
            
            result = await self.add_contact(phone_data)
            self.results.append(result)
            
            if result['success']:
                logger.info(f"✓ 测试成功: {result['message']}")
            else:
                logger.error(f"✗ 测试失败: {result['message']}")
            
        except Exception as e:
            logger.error(f"测试过程中发生错误: {e}")
        finally:
            # 断开MCP服务器连接
            await self.disconnect_from_mcp_server()


def main():
    """主函数"""
    EXCEL_FILE_PATH = "9.29北广线索.xlsx"
    
    # 创建添加器实例
    adder = WechatContactAdder(EXCEL_FILE_PATH)
    
    try:
        print("=" * 60)
        print("微信联系人批量添加工具")
        print("=" * 60)
        print("1. 测试单个联系人（第一个）")
        print("2. 批量添加所有联系人")
        print("3. 批量添加前10个联系人（测试用）")
        print("=" * 60)
        
        choice = input("请选择操作 (1/2/3): ").strip()
        
        if choice == "1":
            logger.info("开始测试单个联系人...")
            asyncio.run(adder.test_single_contact(0))
        elif choice == "2":
            confirm = input("确认要添加所有联系人吗？(y/N): ").strip().lower()
            if confirm == 'y':
                logger.info("开始批量添加所有联系人...")
                asyncio.run(adder.batch_add_contacts(delay_seconds=3))  # 3秒延迟，避免过于频繁
            else:
                logger.info("操作已取消")
        elif choice == "3":
            logger.info("开始批量添加前10个联系人（测试）...")
            asyncio.run(adder.batch_add_contacts(delay_seconds=2, max_contacts=10))
        else:
            logger.error("无效选择")
            
    except Exception as e:
        logger.error(f"程序执行失败: {e}")


if __name__ == "__main__":
    main()
