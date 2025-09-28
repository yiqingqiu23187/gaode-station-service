#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP微信联系人测试脚本
测试连接MCP服务器并添加微信联系人
"""

import asyncio
import logging
from typing import Optional
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MCPWechatTester:
    def __init__(self):
        """初始化MCP微信测试器"""
        self.session: Optional[ClientSession] = None
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
            logger.info(f"🔗 正在连接到MCP服务器: {self.mcp_config['url']}")

            self._streams_context = streamablehttp_client(
                url=self.mcp_config['url'],
                headers=self.mcp_config['headers'],
            )
            read_stream, write_stream, _ = await self._streams_context.__aenter__()

            self._session_context = ClientSession(read_stream, write_stream)
            self.session = await self._session_context.__aenter__()

            await self.session.initialize()
            logger.info("✅ 成功连接到MCP服务器")

            # 列出可用工具
            response = await self.session.list_tools()
            available_tools = [tool.name for tool in response.tools]
            logger.info(f"🛠️  可用工具: {', '.join(available_tools)}")

            return True

        except Exception as e:
            logger.error(f"❌ 连接MCP服务器失败: {e}")
            return False

    async def disconnect_from_mcp_server(self):
        """断开MCP服务器连接"""
        try:
            if self._session_context:
                await self._session_context.__aexit__(None, None, None)
            if self._streams_context:
                await self._streams_context.__aexit__(None, None, None)
            logger.info("🔌 已断开MCP服务器连接")
        except Exception as e:
            logger.error(f"⚠️  断开MCP服务器连接时发生错误: {e}")

    async def test_add_wechat_contact(self, phone_number: str, name: str = "测试联系人"):
        """测试添加微信联系人"""
        try:
            if not self.session:
                logger.error("❌ MCP会话未初始化，请先连接到服务器")
                return False

            logger.info(f"📱 正在测试添加微信联系人: {name} ({phone_number})")

            # 调用MCP工具创建添加联系人任务
            tool_args = {
                "phoneNumber": phone_number,
                "name": name
            }

            logger.info(f"🔧 调用工具参数: {tool_args}")

            # 调用createAddContactTask工具
            result = await self.session.call_tool("createAddContactTask", tool_args)

            # 解析MCP调用结果
            if result.isError:
                error_message = f"MCP调用失败: {result.content}"
                logger.error(f"❌ {error_message}")
                return False
            else:
                success_message = f"任务已创建: {result.content}"
                logger.info(f"✅ MCP调用成功: {success_message}")
                return True

        except Exception as e:
            logger.error(f"❌ 测试添加微信联系人失败: {e}")
            return False

    async def test_list_tools(self):
        """测试列出所有可用工具"""
        try:
            if not self.session:
                logger.error("❌ MCP会话未初始化，请先连接到服务器")
                return False

            logger.info("🔍 获取所有可用工具...")

            response = await self.session.list_tools()

            logger.info(f"📋 找到 {len(response.tools)} 个工具:")
            for i, tool in enumerate(response.tools, 1):
                logger.info(f"  {i}. {tool.name}")
                if hasattr(tool, 'description') and tool.description:
                    logger.info(f"     描述: {tool.description}")
                if hasattr(tool, 'inputSchema') and tool.inputSchema:
                    logger.info(f"     参数: {tool.inputSchema}")
                logger.info("")

            return True

        except Exception as e:
            logger.error(f"❌ 获取工具列表失败: {e}")
            return False

async def main():
    """主测试函数"""
    logger.info("🚀 开始MCP微信联系人测试")

    tester = MCPWechatTester()

    try:
        # 1. 连接MCP服务器
        logger.info("\n" + "="*50)
        logger.info("步骤 1: 连接MCP服务器")
        logger.info("="*50)

        connected = await tester.connect_to_mcp_server()
        if not connected:
            logger.error("❌ 无法连接到MCP服务器，测试终止")
            return

        # 2. 列出可用工具
        logger.info("\n" + "="*50)
        logger.info("步骤 2: 列出可用工具")
        logger.info("="*50)

        await tester.test_list_tools()

        # 3. 测试添加微信联系人
        logger.info("\n" + "="*50)
        logger.info("步骤 3: 测试添加微信联系人")
        logger.info("="*50)

        test_phone = "13501115949"
        test_name = "测试用户"

        success = await tester.test_add_wechat_contact(test_phone, test_name)

        if success:
            logger.info(f"🎉 测试成功！已为手机号 {test_phone} 创建微信添加任务")
        else:
            logger.error(f"💥 测试失败！无法为手机号 {test_phone} 创建微信添加任务")

        # 4. 等待一段时间观察结果
        logger.info("\n" + "="*50)
        logger.info("步骤 4: 等待处理结果")
        logger.info("="*50)

        logger.info("⏳ 等待 5 秒观察处理结果...")
        await asyncio.sleep(5)

    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")

    finally:
        # 5. 断开连接
        logger.info("\n" + "="*50)
        logger.info("步骤 5: 清理资源")
        logger.info("="*50)

        await tester.disconnect_from_mcp_server()
        logger.info("🏁 测试完成")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())
