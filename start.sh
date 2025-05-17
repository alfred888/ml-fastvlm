#!/bin/bash

# 设置错误时退出
set -e

# 定义颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}开始启动服务...${NC}"

# 检查是否存在虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}创建虚拟环境...${NC}"
    python3 -m venv venv
fi

# 激活虚拟环境
echo -e "${YELLOW}激活虚拟环境...${NC}"
source venv/bin/activate

# 安装依赖
echo -e "${YELLOW}安装依赖...${NC}"
pip install -r requirements.txt

# 检查checkpoints目录
if [ ! -d "checkpoints" ]; then
    echo -e "${YELLOW}创建checkpoints目录...${NC}"
    mkdir -p checkpoints
fi

# 启动服务
echo -e "${GREEN}启动服务...${NC}"
python server.py

# 捕获Ctrl+C信号
trap 'echo -e "${YELLOW}正在关闭服务...${NC}"; deactivate' INT

# 保持脚本运行
wait 