# 简历管理Web应用

一个基于Flask的Web应用，用于批量处理简历数据，整合了简历导入、微信联系人添加和外呼任务创建功能。

## 功能特性

### 🚀 核心功能
- **简历入库** - 从Excel文件批量导入简历数据到数据库
- **微信添加** - 根据手机号自动添加微信联系人
- **智能等待** - 根据联系人数量计算等待时间
- **外呼任务** - 自动创建外呼任务

### 📊 界面特性
- **现代化UI** - 基于Bootstrap 5的响应式设计
- **实时进度** - 实时显示处理进度和状态
- **拖拽上传** - 支持拖拽上传Excel文件
- **详细报告** - 完整的处理结果和统计信息

## 系统要求

### 环境依赖
- Python 3.8+
- MySQL 5.7+
- MCP服务器 (用于微信和外呼功能)

### Python包依赖
```bash
Flask==2.3.3
pandas==2.0.3
pymysql==1.1.0
openpyxl==3.1.2
xlrd==2.0.1
mcp==1.0.0
Werkzeug==2.3.7
Jinja2==3.1.2
cryptography==41.0.4
```

## 安装部署

### 1. 克隆代码
```bash
git clone <repository-url>
cd resume-management-app
```

### 2. 安装依赖
```bash
pip install -r requirements_resume_app.txt
```

### 3. 配置环境变量
创建 `.env` 文件：
```bash
# 数据库配置
DATABASE_URL=mysql://username:password@localhost:3306/resume_db

# MCP服务器配置
MCP_SERVER_URL=http://152.136.8.68:3001/mcp

# Flask配置
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# 日志级别
LOG_LEVEL=INFO
```

### 4. 数据库设置
确保MySQL数据库中存在 `resumes` 表，表结构应包含以下字段：
```sql
CREATE TABLE resumes (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    wechat VARCHAR(50),
    age VARCHAR(10),
    expect_location VARCHAR(100),
    expect_positions TEXT,
    source VARCHAR(20) DEFAULT 'INTERNAL',
    deleted TINYINT DEFAULT 0,
    create_time DATETIME,
    update_time DATETIME
);
```

### 5. 启动应用
```bash
python app.py
```

应用将在 `http://localhost:5000` 启动。

## 使用说明

### 1. Excel文件格式要求

Excel文件应包含以下列（列名必须完全匹配）：

| 列名 | 必填 | 说明 | 示例 |
|------|------|------|------|
| 姓名 | ✅ | 应聘者姓名 | 张三 |
| 手机号 | ✅ | 联系电话 | 13800138000 |
| 年龄 | ❌ | 年龄范围或具体年龄 | 25~35岁 或 28岁 |
| 居住城市 | ❌ | 居住地或工作城市 | 北京 |
| 工作城市 | ❌ | 工作城市（备选） | 上海 |
| 应聘岗位 | ❌ | 期望职位 | 分拣员 |
| 微信号 | ❌ | 微信号 | zhangsan123 |

### 2. 操作流程

1. **访问首页** - 打开浏览器访问应用地址
2. **输入职位ID** - 填写用于创建外呼任务的职位ID
3. **上传Excel文件** - 拖拽或选择Excel文件上传
4. **开始处理** - 点击"开始处理"按钮
5. **查看进度** - 系统会自动跳转到状态页面显示实时进度
6. **等待完成** - 系统会按顺序执行所有步骤

### 3. 处理步骤详解

#### 步骤1: 简历入库 (10% - 30%)
- 读取Excel文件内容
- 数据格式转换和验证
- 批量插入数据库
- 生成简历ID列表

#### 步骤2: 添加微信联系人 (30% - 60%)
- 提取手机号和姓名
- 调用MCP服务创建微信添加任务
- 记录成功和失败的联系人

#### 步骤3: 等待处理完成 (60% - 80%)
- 根据联系人数量计算等待时间（每人30秒）
- 显示倒计时
- 等待微信添加任务完成

#### 步骤4: 添加外呼任务 (80% - 100%)
- 匹配简历ID和手机号
- 调用MCP服务创建外呼任务
- 完成整个流程

## 配置说明

### 环境配置
应用支持多环境配置：
- `development` - 开发环境
- `production` - 生产环境
- `testing` - 测试环境

### 主要配置项
```python
# 文件上传
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

# 微信添加等待时间
WECHAT_WAIT_TIME_PER_CONTACT = 30  # 秒

# MCP连接超时
MCP_TIMEOUT = 50  # 秒
```

## API接口

### GET /api/status
获取当前处理状态

**响应示例：**
```json
{
    "step": "importing",
    "progress": 25,
    "message": "正在导入简历数据...",
    "wait_until": null,
    "results": {
        "import": {
            "success": true,
            "total_records": 100,
            "successful_count": 95,
            "failed_count": 5
        }
    }
}
```

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库URL配置
   - 确认数据库服务运行状态
   - 验证用户名密码

2. **MCP服务器连接失败**
   - 检查MCP服务器地址
   - 确认网络连通性
   - 查看MCP服务器状态

3. **Excel文件读取失败**
   - 确认文件格式为.xlsx或.xls
   - 检查列名是否正确
   - 验证文件是否损坏

4. **简历导入失败**
   - 检查数据库表结构
   - 确认必填字段不为空
   - 查看详细错误日志

### 日志查看
应用日志保存在 `resume_management.log` 文件中，包含详细的操作记录和错误信息。

## 开发说明

### 项目结构
```
├── app.py                 # 主应用文件
├── config.py             # 配置文件
├── requirements_resume_app.txt  # 依赖包列表
├── templates/            # HTML模板
│   ├── base.html        # 基础模板
│   ├── index.html       # 首页模板
│   └── status.html      # 状态页面模板
├── uploads/             # 文件上传目录
└── logs/                # 日志目录
```

### 扩展开发
- 添加新的数据源支持
- 集成更多的通讯工具
- 增加数据验证规则
- 优化批处理性能

## 许可证

本项目采用 MIT 许可证。

## 支持

如有问题或建议，请联系开发团队。
