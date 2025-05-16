from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
from typing import List
import json
import asyncio
import cv2
import os
from datetime import datetime
import threading
import queue

app = FastAPI()

# 图片处理配置
IMAGE_WIDTH = 640  # 压缩后的图片宽度
IMAGE_QUALITY = 85  # JPEG压缩质量（0-100）
JPEG_EXTENSION = '.jpg'

# 全局变量
camera = None
capture_lock = threading.Lock()
active_connections: List[WebSocket] = []

# 创建图片保存目录
IMAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captured_images")
os.makedirs(IMAGE_DIR, exist_ok=True)

def print_progress(message):
    """打印带时间戳的进度信息"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def get_camera():
    """获取摄像头对象"""
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)
        # 设置摄像头参数
        camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
        camera.set(cv2.CAP_PROP_EXPOSURE, -4)
        camera.set(cv2.CAP_PROP_GAIN, 100)
        camera.set(cv2.CAP_PROP_BRIGHTNESS, 150)
    return camera

def compress_image(frame):
    """压缩图片到指定尺寸和质量"""
    # 计算压缩后的高度，保持宽高比
    height = int(frame.shape[0] * (IMAGE_WIDTH / frame.shape[1]))
    
    # 调整图片大小
    resized = cv2.resize(frame, (IMAGE_WIDTH, height), interpolation=cv2.INTER_AREA)
    
    return resized

def save_image(frame, filepath):
    """保存压缩后的图片"""
    # 压缩图片
    compressed = compress_image(frame)
    
    # 保存为JPEG格式，指定压缩质量
    cv2.imwrite(filepath, compressed, [cv2.IMWRITE_JPEG_QUALITY, IMAGE_QUALITY])
    
    # 获取压缩后的文件大小
    file_size = os.path.getsize(filepath) / 1024  # 转换为KB
    print_progress(f"📊 图片大小: {file_size:.1f}KB")
    
    return compressed

async def capture_and_send(websocket):
    """捕获图片并发送到服务器"""
    while True:
        with capture_lock:
            try:
                camera = get_camera()
                ret, frame = camera.read()
                if not ret:
                    print_progress("❌ 无法读取摄像头画面")
                    await asyncio.sleep(1)
                    continue

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"captured_image_{timestamp}{JPEG_EXTENSION}"
                filepath = os.path.join(IMAGE_DIR, filename)
                
                # 保存压缩后的图片
                compressed_frame = save_image(frame, filepath)
                print_progress(f"📸 图片已保存到: {filepath}")
                
                # 读取压缩后的图片数据
                with open(filepath, 'rb') as f:
                    image_data = f.read()
                
                # 发送图片数据到服务器
                await websocket.send_bytes(image_data)
                
                # 删除临时文件
                try:
                    os.remove(filepath)
                    print_progress(f"🗑️ 临时文件已删除: {filepath}")
                except Exception as e:
                    print_progress(f"⚠️ 删除临时文件失败: {e}")
                
            except Exception as e:
                print_progress(f"❌ 处理过程出错: {e}")
        
        await asyncio.sleep(5)  # 每5秒拍摄一次

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 连接处理"""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        # 启动图片捕获和发送任务
        capture_task = asyncio.create_task(capture_and_send(websocket))
        
        # 等待服务器返回的描述结果
        while True:
            data = await websocket.receive_text()
            try:
                result = json.loads(data)
                if result.get("type") == "description":
                    # 广播描述结果给所有连接的客户端
                    for connection in active_connections:
                        try:
                            await connection.send_json(result)
                        except:
                            continue
            except json.JSONDecodeError:
                print_progress("❌ 收到无效的JSON数据")
                
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        if 'capture_task' in locals():
            capture_task.cancel()

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get():
    """返回主页"""
    with open("templates/index.html") as f:
        return f.read()

if __name__ == "__main__":
    print_progress("🚀 启动树莓派客户端...")
    uvicorn.run(app, host="0.0.0.0", port=8080) 