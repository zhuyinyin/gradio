"""
@Project : ComfyUI
@File : get_files.py
@Author : Yann Zhu
@Date : 2024/12/21 09:43
"""
import threading
import requests
import zipfile
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Dict
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# 创建 FastAPI 应用
app = FastAPI(title="File Service")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class FileRequest(BaseModel):
    database_url: str    # 数据库连接字符串
    task_id: int        # 任务ID
    toolkit_url: str    # Toolkit URL

def get_file(database_url: str, task_id: int, toolkit_url: str):
    async def callback(database_url: str, task_id: int, toolkit_url: str):
        print(f"执行任务 ID: {task_id}")
        
        try:
            # 创建数据库连接
            engine = create_engine(database_url)
            Session = sessionmaker(bind=engine)
            session = Session()
            
            try:
                # 查询任务信息
                task = session.execute(
                    text("SELECT name FROM tasks WHERE id = :task_id"),
                    {"task_id": task_id}
                ).first()
                
                if not task:
                    print(f"未找到任务 ID: {task_id}")
                    return False
                
                job_name = task.name
                
                # 发送请求获取文件
                response = requests.post(
                    f'{toolkit_url}/get_zip/',
                    json={"job_name": job_name}
                )
                
                if response.status_code == 200:
                    zip_content = response.content
                    # 指定要保存的 ZIP 文件的本地路径
                    local_zip_file_path = f"models/loras/{job_name}.zip"

                    # 将 ZIP 文件内容写入到本地文件中
                    with open(local_zip_file_path, 'wb') as f:
                        f.write(zip_content)

                    print(f"ZIP 文件已保存到 {local_zip_file_path}")
                    
                    # 解压文件
                    with zipfile.ZipFile(local_zip_file_path, 'r') as zip_ref:
                        zip_ref.extractall(f"models/loras/{job_name}")
                    
                    print(f"文件已解压到 models/loras/{job_name}")
                    
                    # 更新任务状态为 running
                    session.execute(
                        text("""
                        UPDATE tasks 
                        SET status = 'running'
                        WHERE id = :task_id
                        """),
                        {"task_id": task_id}
                    )
                    session.commit()
                    print(f"任务 {task_id} 状态已更新为 running")
                    
                    return True
                else:
                    print(f"请求失败，状态码: {response.status_code}")
                    return False
                    
            finally:
                session.close()
                
        except Exception as e:
            print(f"处理文件时出错: {str(e)}")
            return False

    # 启动异步任务
    thread = threading.Thread(
        target=asyncio.run,
        args=(callback(database_url, task_id, toolkit_url),)
    )
    thread.start()

    print("主线程继续执行其他任务...")
    return (f"models/loras/task_{task_id}",)

# API 端点
@app.post("/get_file")
async def handle_get_file(request: FileRequest) -> Dict[str, str]:
    """处理获取文件的请求"""
    try:
        result = get_file(
            request.database_url,
            request.task_id,
            request.toolkit_url
        )
        return {"status": "success", "path": result[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}

if __name__ == "__main__":
    # 启动服务器
    uvicorn.run(
        "get_files:app",
        host="0.0.0.0",
        port=8000,
        reload=True,      # 开发模式下自动重载
        workers=1         # 工作进程数
    )