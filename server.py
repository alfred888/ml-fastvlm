from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import cv2
import subprocess
import os
from datetime import datetime
import asyncio
import json
import uvicorn
from typing import List, Dict
import threading
import queue
import time
import numpy as np

app = FastAPI()

# FastVLM 模型路径
MODEL_PATH = "/Users/user/workspace/models/llava-fastvithd_0.5b_stage3"
PROMPT = "用简短的语言描述图片内容"

# 全局变量
description_queue = queue.Queue()
is_model_loading = True
active_connections: List[WebSocket] = []

# 创建图片保存目录
IMAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captured_images")
os.makedirs(IMAGE_DIR, exist_ok=True)

def print_progress(message):
    """打印带时间戳的进度信息"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def save_image(image_data, filepath):
    """保存图片数据到文件"""
    # 将二进制数据转换为numpy数组
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 保存图片
    cv2.imwrite(filepath, img)
    
    # 获取文件大小
    file_size = os.path.getsize(filepath) / 1024  # 转换为KB
    print_progress(f"📊 接收到的图片大小: {file_size:.1f}KB")
    
    return img

def describe_image(image_path):
    """调用 FastVLM 模型描述图像内容"""
    global is_model_loading
    
    cmd = [
        "python", "predict.py",
        "--model-path", MODEL_PATH,
        "--image-file", image_path,
        "--prompt", PROMPT
    ]
    
    print_progress(f"🔍 正在描述图片: {image_path}")
    print_progress(f"📝 使用的提示词: {PROMPT}")
    
    if is_model_loading:
        print_progress("⏳ 首次运行，模型正在加载中...")
        is_model_loading = False
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    description = result.stdout.strip()
    error = result.stderr.strip()
    
    if error:
        print_progress(f"❌ 错误信息:")
        print("=" * 50)
        print(error)
        print("=" * 50)
        return f"处理出错: {error}"
    
    if not description:
        print_progress("⚠️ 警告: 模型没有返回任何描述")
        return "模型没有返回任何描述"
    
    print_progress("✨ 描述结果:")
    print("=" * 50)
    print(description)
    print("=" * 50)
    print()
    
    return description

async def process_image(websocket, image_data):
    """处理接收到的图片数据"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"received_image_{timestamp}.jpg"
        filepath = os.path.join(IMAGE_DIR, filename)
        
        # 保存图片
        save_image(image_data, filepath)
        print_progress(f"📸 图片已保存到: {filepath}")
        
        # 确保文件存在
        if not os.path.exists(filepath):
            print_progress(f"❌ 图片文件保存失败: {filepath}")
            return
        
        # 在后台线程中运行描述任务
        loop = asyncio.get_event_loop()
        description = await loop.run_in_executor(None, describe_image, filepath)
        
        # 发送描述结果回树莓派
        await websocket.send_json({
            "type": "description",
            "content": description,
            "timestamp": timestamp
        })
        
        # 删除临时文件
        try:
            os.remove(filepath)
            print_progress(f"🗑️ 临时文件已删除: {filepath}")
        except Exception as e:
            print_progress(f"⚠️ 删除临时文件失败: {e}")
            
    except Exception as e:
        print_progress(f"❌ 处理图片时出错: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 连接处理"""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # 接收图片数据
            image_data = await websocket.receive_bytes()
            # 处理图片
            await process_image(websocket, image_data)
    except WebSocketDisconnect:
        active_connections.remove(websocket)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get():
    """返回主页"""
    with open("templates/index.html") as f:
        return f.read()

if __name__ == "__main__":
    print_progress("🚀 启动服务器...")
    uvicorn.run(app, host="0.0.0.0", port=5000) 