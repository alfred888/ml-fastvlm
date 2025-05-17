#!/bin/bash

# 检查 NVIDIA 驱动
if ! command -v nvidia-smi &> /dev/null; then
    echo "错误: 未检测到 NVIDIA 驱动，请先安装 NVIDIA 驱动"
    exit 1
fi

# 检查 NVIDIA 驱动版本
NVIDIA_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader)
echo "检测到 NVIDIA 驱动版本: $NVIDIA_VERSION"

# 检查 CUDA 工具包
if ! command -v nvcc &> /dev/null; then
    echo "警告: 未检测到 CUDA 工具包 (nvcc)，但不会影响容器运行"
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

# 检查 GPU 状态和内存
echo "GPU 状态:"
nvidia-smi --query-gpu=name,memory.total,memory.free,memory.used --format=csv,noheader

# 检查 GPU 数量
GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
echo "检测到 $GPU_COUNT 个 GPU 设备"

# 检查 Docker 是否运行
if ! docker info &> /dev/null; then
    echo "错误: Docker 未运行，请先启动 Docker 服务"
    exit 1
fi

# 检查 Docker 版本
DOCKER_VERSION=$(docker --version)
echo "Docker 版本: $DOCKER_VERSION"

# 检查 nvidia-container-toolkit
if ! docker info | grep -i "nvidia" &> /dev/null; then
    echo "警告: 未检测到 nvidia-container-toolkit，请确保已安装"
    echo "安装命令:"
    echo "distribution=$(. /etc/os-release;echo $ID$VERSION_ID)"
    echo "curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -"
    echo "curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list"
    echo "sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit"
    echo "sudo systemctl restart docker"
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

# 检查端口占用
if lsof -i :5000 &> /dev/null; then
    echo "错误: 端口 5000 已被占用，请先释放该端口"
    exit 1
fi

echo "环境检查通过，开始启动服务..."
docker-compose up --build 