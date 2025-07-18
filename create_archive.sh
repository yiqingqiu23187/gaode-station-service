#!/bin/bash

# 脚本功能：将指定的文件夹打包成一个 .tar.gz 压缩文件。

# --- 配置 ---
# 要打包的文件夹的完整路径
SOURCE_DIRECTORY="/Users/fbi/Documents/gaode"
# 输出的压缩包文件名 (将保存在 SOURCE_DIRECTORY 的上一级目录中)
OUTPUT_FILENAME="gaode.tar.gz"

# --- 脚本主体 ---

# 检查源文件夹是否存在
if [ ! -d "$SOURCE_DIRECTORY" ]; then
  echo "错误：指定的源文件夹不存在: $SOURCE_DIRECTORY"
  exit 1
fi

# 获取源文件夹的父目录和基本名称
PARENT_DIR=$(dirname "$SOURCE_DIRECTORY")
BASE_NAME=$(basename "$SOURCE_DIRECTORY")

# 定义输出文件的完整路径
OUTPUT_PATH="$PARENT_DIR/$OUTPUT_FILENAME"

echo "准备打包文件夹: $SOURCE_DIRECTORY"
echo "输出文件将是: $OUTPUT_PATH"

# 使用 tar 命令进行打包和压缩
# - C: 先切换到指定的目录 (这里是父目录)，这样可以避免在压缩包中包含完整的绝对路径
# - c: 创建一个新的归档文件
# - z: 使用 gzip 进行压缩 (生成 .gz 后缀)
# - v: 显示过程中的详细信息
# - f: 指定归- 档文件的名称
tar -C "$PARENT_DIR" -czvf "$OUTPUT_PATH" "$BASE_NAME"

# 检查 tar 命令是否成功执行
if [ $? -eq 0 ]; then
  echo ""
  echo "打包成功！"
  echo "压缩包已保存至: $OUTPUT_PATH"
else
  echo ""
  echo "打包失败。"
  exit 1
fi 