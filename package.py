#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简历管理应用打包脚本
将应用打包成可分发的格式
"""

import os
import sys
import shutil
import zipfile
import tarfile
from datetime import datetime
from pathlib import Path

class ResumeAppPackager:
    def __init__(self):
        self.app_name = "resume-management-app"
        self.version = "1.0.0"
        self.build_dir = "build"
        self.dist_dir = "dist"

        # 需要包含的文件和目录
        self.include_files = [
            "app.py",
            "config.py",
            "test_mcp_wechat.py",
            "requirements_resume_app.txt",
            "README_resume_app.md",
            "run_resume_app.sh",
            "setup.py",
            "templates/",
            "static/",
            "resumeifo_collecting/"
        ]

        # 需要排除的文件和目录
        self.exclude_patterns = [
            "__pycache__",
            "*.pyc",
            "*.pyo",
            ".git",
            ".gitignore",
            "*.log",
            "uploads/",
            "build/",
            "dist/",
            ".env",
            "venv/",
            ".vscode/",
            ".idea/",
            "*.db",
            "*.tar",
            "*.zip"
        ]

    def clean_build_dirs(self):
        """清理构建目录"""
        print("🧹 清理构建目录...")
        for dir_name in [self.build_dir, self.dist_dir]:
            if os.path.exists(dir_name):
                shutil.rmtree(dir_name)
            os.makedirs(dir_name, exist_ok=True)

    def should_exclude(self, file_path):
        """检查文件是否应该被排除"""
        for pattern in self.exclude_patterns:
            if pattern in file_path or file_path.endswith(pattern.replace("*", "")):
                return True
        return False

    def copy_files(self, target_dir):
        """复制应用文件到目标目录"""
        print("📁 复制应用文件...")

        for item in self.include_files:
            src_path = Path(item)
            if not src_path.exists():
                print(f"⚠️  警告: {item} 不存在，跳过")
                continue

            dst_path = Path(target_dir) / item

            if src_path.is_file():
                # 复制文件
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
                print(f"  ✓ {item}")
            elif src_path.is_dir():
                # 复制目录
                self.copy_directory(src_path, dst_path)
                print(f"  ✓ {item}/")

    def copy_directory(self, src_dir, dst_dir):
        """递归复制目录，排除不需要的文件"""
        dst_dir.mkdir(parents=True, exist_ok=True)

        for item in src_dir.rglob("*"):
            if self.should_exclude(str(item)):
                continue

            relative_path = item.relative_to(src_dir)
            dst_item = dst_dir / relative_path

            if item.is_file():
                dst_item.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst_item)

    def create_startup_script(self, target_dir):
        """创建启动脚本"""
        print("🚀 创建启动脚本...")

        # Windows批处理文件
        bat_content = """@echo off
echo 启动简历管理应用...
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

REM 创建虚拟环境
if not exist "venv" (
    echo 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
call venv\\Scripts\\activate.bat

REM 安装依赖
echo 安装依赖包...
pip install -r requirements_resume_app.txt

REM 创建必要目录
if not exist "uploads" mkdir uploads
if not exist "logs" mkdir logs

REM 启动应用
echo 启动Web应用...
echo 访问地址: http://localhost:5000
echo 按 Ctrl+C 停止应用
echo.
python app.py

pause
"""

        with open(Path(target_dir) / "start.bat", "w", encoding="utf-8") as f:
            f.write(bat_content)

        # Linux/Mac shell脚本
        sh_content = """#!/bin/bash

echo "🚀 启动简历管理应用..."
echo

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3，请先安装Python 3.8+"
    exit 1
fi

python_version=$(python3 --version 2>&1)
echo "Python版本: $python_version"

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📚 安装依赖包..."
pip install -r requirements_resume_app.txt

# 创建必要目录
echo "📁 创建必要目录..."
mkdir -p uploads logs

# 启动应用
echo "🌟 启动Web应用..."
echo "访问地址: http://localhost:5000"
echo "按 Ctrl+C 停止应用"
echo

python app.py
"""

        sh_file = Path(target_dir) / "start.sh"
        with open(sh_file, "w", encoding="utf-8") as f:
            f.write(sh_content)

        # 设置执行权限
        os.chmod(sh_file, 0o755)

    def create_readme(self, target_dir):
        """创建部署说明文件"""
        print("📝 创建部署说明...")

        readme_content = f"""# 简历管理应用 v{self.version}

## 快速开始

### Windows用户
1. 双击 `start.bat` 启动应用
2. 等待依赖安装完成
3. 打开浏览器访问 http://localhost:5000

### Linux/Mac用户
1. 在终端中运行: `./start.sh`
2. 等待依赖安装完成
3. 打开浏览器访问 http://localhost:5000

## 系统要求

- Python 3.8 或更高版本
- 网络连接（用于安装依赖包）
- MySQL数据库（可选，用于生产环境）

## 配置说明

### 数据库配置
编辑 `config.py` 文件，修改数据库连接信息：

```python
DATABASE_URL = 'mysql://username:password@localhost:3306/resume_db'
```

### MCP服务器配置
如需使用微信和外呼功能，请配置MCP服务器地址：

```python
MCP_SERVER_URL = 'http://your-mcp-server:3001/mcp'
```

## 功能说明

1. **简历导入** - 从Excel文件批量导入简历数据
2. **微信添加** - 自动添加微信联系人
3. **外呼任务** - 创建外呼任务
4. **进度监控** - 实时查看处理进度

## 文件说明

- `app.py` - 主应用文件
- `config.py` - 配置文件
- `templates/` - HTML模板
- `static/` - 静态资源（CSS、JS、图片）
- `requirements_resume_app.txt` - Python依赖包列表

## 故障排除

### 常见问题

1. **端口被占用**
   - 修改 `app.py` 中的端口号
   - 或者停止占用5000端口的其他程序

2. **依赖安装失败**
   - 检查网络连接
   - 尝试使用国内镜像源

3. **数据库连接失败**
   - 检查数据库服务是否启动
   - 验证连接信息是否正确

## 技术支持

如有问题，请联系开发团队。

---
构建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
版本: {self.version}
"""

        with open(Path(target_dir) / "部署说明.md", "w", encoding="utf-8") as f:
            f.write(readme_content)

    def create_zip_package(self, source_dir):
        """创建ZIP压缩包"""
        print("📦 创建ZIP压缩包...")

        zip_name = f"{self.app_name}-{self.version}.zip"
        zip_path = Path(self.dist_dir) / zip_name

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = Path(root) / file
                    arc_path = file_path.relative_to(source_dir)
                    zipf.write(file_path, arc_path)

        print(f"  ✓ {zip_name}")
        return zip_path

    def create_tar_package(self, source_dir):
        """创建TAR.GZ压缩包"""
        print("📦 创建TAR.GZ压缩包...")

        tar_name = f"{self.app_name}-{self.version}.tar.gz"
        tar_path = Path(self.dist_dir) / tar_name

        with tarfile.open(tar_path, 'w:gz') as tarf:
            tarf.add(source_dir, arcname=f"{self.app_name}-{self.version}")

        print(f"  ✓ {tar_name}")
        return tar_path

    def create_installer_package(self, source_dir):
        """创建安装包目录"""
        print("📦 创建安装包目录...")

        installer_dir = Path(self.dist_dir) / f"{self.app_name}-{self.version}-installer"

        # 复制应用文件
        shutil.copytree(source_dir, installer_dir)

        # 创建安装脚本
        install_script = installer_dir / "install.py"
        install_content = """#!/usr/bin/env python3
# 简历管理应用安装脚本

import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    print("🚀 简历管理应用安装程序")
    print("=" * 40)

    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ 错误: 需要Python 3.8或更高版本")
        sys.exit(1)

    print(f"✓ Python版本: {sys.version}")

    # 安装目录
    install_dir = Path.home() / "resume-management-app"

    if install_dir.exists():
        response = input(f"目录 {install_dir} 已存在，是否覆盖？(y/N): ")
        if response.lower() != 'y':
            print("安装已取消")
            sys.exit(0)
        shutil.rmtree(install_dir)

    # 复制文件
    print(f"📁 安装到: {install_dir}")
    current_dir = Path(__file__).parent
    shutil.copytree(current_dir, install_dir, ignore=shutil.ignore_patterns('install.py'))

    # 创建虚拟环境
    print("📦 创建虚拟环境...")
    venv_dir = install_dir / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

    # 安装依赖
    print("📚 安装依赖包...")
    pip_path = venv_dir / ("Scripts" if os.name == "nt" else "bin") / "pip"
    subprocess.run([str(pip_path), "install", "-r", str(install_dir / "requirements_resume_app.txt")], check=True)

    # 创建桌面快捷方式（Windows）
    if os.name == "nt":
        try:
            import winshell
            from win32com.client import Dispatch

            desktop = winshell.desktop()
            shortcut_path = os.path.join(desktop, "简历管理应用.lnk")

            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = str(install_dir / "start.bat")
            shortcut.WorkingDirectory = str(install_dir)
            shortcut.IconLocation = str(install_dir / "static" / "images" / "icon.ico")
            shortcut.save()

            print("✓ 已创建桌面快捷方式")
        except ImportError:
            print("⚠️  无法创建桌面快捷方式（缺少winshell模块）")

    print("🎉 安装完成！")
    print(f"应用目录: {install_dir}")
    print("启动方式:")
    if os.name == "nt":
        print(f"  Windows: 双击 {install_dir / 'start.bat'}")
    else:
        print(f"  Linux/Mac: 运行 {install_dir / 'start.sh'}")

if __name__ == "__main__":
    main()
"""

        with open(install_script, "w", encoding="utf-8") as f:
            f.write(install_content)

        print(f"  ✓ {installer_dir.name}")
        return installer_dir

    def generate_checksums(self):
        """生成校验和文件"""
        print("🔐 生成校验和...")

        import hashlib

        checksums = {}

        for file_path in Path(self.dist_dir).glob("*"):
            if file_path.is_file() and not file_path.name.endswith('.md5'):
                with open(file_path, 'rb') as f:
                    content = f.read()
                    md5_hash = hashlib.md5(content).hexdigest()
                    checksums[file_path.name] = md5_hash

        # 写入校验和文件
        checksum_file = Path(self.dist_dir) / "checksums.md5"
        with open(checksum_file, 'w') as f:
            for filename, checksum in checksums.items():
                f.write(f"{checksum}  {filename}\n")

        print(f"  ✓ checksums.md5")

    def package(self):
        """执行完整的打包流程"""
        print(f"📦 开始打包 {self.app_name} v{self.version}")
        print("=" * 50)

        try:
            # 1. 清理构建目录
            self.clean_build_dirs()

            # 2. 创建构建目录
            build_app_dir = Path(self.build_dir) / f"{self.app_name}-{self.version}"
            build_app_dir.mkdir(parents=True, exist_ok=True)

            # 3. 复制文件
            self.copy_files(build_app_dir)

            # 4. 创建启动脚本
            self.create_startup_script(build_app_dir)

            # 5. 创建部署说明
            self.create_readme(build_app_dir)

            # 6. 创建各种格式的包
            zip_path = self.create_zip_package(build_app_dir)
            tar_path = self.create_tar_package(build_app_dir)
            installer_dir = self.create_installer_package(build_app_dir)

            # 7. 生成校验和
            self.generate_checksums()

            print("\n🎉 打包完成！")
            print("=" * 50)
            print("生成的文件:")
            for item in Path(self.dist_dir).iterdir():
                size = item.stat().st_size if item.is_file() else "目录"
                print(f"  📁 {item.name} ({size} bytes)" if isinstance(size, int) else f"  📁 {item.name} ({size})")

            print(f"\n📍 输出目录: {Path(self.dist_dir).absolute()}")

        except Exception as e:
            print(f"\n❌ 打包失败: {e}")
            sys.exit(1)

def main():
    """主函数"""
    packager = ResumeAppPackager()
    packager.package()

if __name__ == "__main__":
    main()
