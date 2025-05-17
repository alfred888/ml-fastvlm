#!/bin/bash

# 检查 NVIDIA 驱动
if ! command -v nvidia-smi &> /dev/null; then
    echo "错误: 未检测到 NVIDIA 驱动，请先安装 NVIDIA 驱动"
    exit 1
fi

# 检查 nvidia-docker
if ! command -v nvidia-docker &> /dev/null; then
    echo "错误: 未检测到 nvidia-docker，请先安装 nvidia-docker"
    echo "安装命令:"
    echo "curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -"
    echo "distribution=$(. /etc/os-release;echo $ID$VERSION_ID)"
    echo "curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list"
    echo "sudo apt-get update && sudo apt-get install -y nvidia-docker2"
    exit 1
fi

# 检查 GPU 状态
if ! nvidia-smi &> /dev/null; then
    echo "错误: NVIDIA 驱动可能未正确加载，请检查 GPU 状态"
    exit 1
fi

# 检查模型目录
if [ ! -d "$HOME/models" ]; then
    echo "创建模型目录: $HOME/models"
    mkdir -p "$HOME/models"
fi

# 检查日志目录
if [ ! -d "$HOME/logs" ]; then
    echo "创建日志目录: $HOME/logs"
    mkdir -p "$HOME/logs"
fi

# 检查 Docker 是否运行
if ! docker info &> /dev/null; then
    echo "错误: Docker 未运行，请先启动 Docker 服务"
    exit 1
fi

# 检查端口占用
if lsof -i :5000 &> /dev/null; then
    echo "错误: 端口 5000 已被占用，请先释放该端口"
    exit 1
fi

echo "环境检查通过，开始启动服务..."
docker-compose up --build 