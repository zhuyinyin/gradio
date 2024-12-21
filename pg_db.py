from sqlalchemy import create_engine, Column, Integer, String, JSON, Enum, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum
import os
import pandas as pd

# 从环境变量获取数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://gradio:gradioEVENT12@127.0.0.1:5432/postgres"
)

Base = declarative_base()

class TaskStatus(enum.Enum):
    """任务状态枚举类"""
    PENDING = "pending"     # 等待中
    TRAINING = "training"   # 训练中
    RUN_BEFORE = "run_before" # 运行前
    RUNNING = "running"     # 运行中
    COMPLETED = "completed" # 已完成
    FAILED = "failed"       # 失败

class Task(Base):
    """任务模型类"""
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, index=True, unique=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, index=True)
    config = Column(JSON, nullable=False)
    result_images = Column(JSON, nullable=True, default=list)  # 存储OSS链接列表
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Task(id={self.id}, name='{self.name}', status={self.status.value})>"

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "config": self.config,
            "result_images": self.result_images or [],  # 确保返回空列表而不是None
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

def get_task_list():
    """查询数据库中的任务并返回"""
    db = next(get_db())
    try:
        # 按创建时间倒序排序
        tasks = db.query(Task).order_by(Task.created_at.desc()).all()
        
        # 准备表头和数据
        headers = ["ID", "Name", "Status", "Results", "Created", "Updated"]
        data = []
        for task in tasks:
            result_count = len(task.result_images) if task.result_images else 0
            data.append([
                task.id,                                         # ID
                task.name,                                       # Name
                task.status.value,                              # Status
                "✅ 查看结果" if result_count > 0 else "❌ 无结果",  # Results
                task.created_at.strftime("%Y-%m-%d %H:%M:%S"),  # Created
                task.updated_at.strftime("%Y-%m-%d %H:%M:%S")   # Updated
            ])
        return {
            "headers": headers,
            "data": data
        }
    finally:
        db.close()

def init_db(drop_all=False):
    """初始化数据库
    :param drop_all: 是否删除所有表并重新创建
    """
    if drop_all:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800
)

# 创建 session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_task_name_exists(task_name: str) -> bool:
    """检查任务名称是否已存在
    
    Args:
        task_name: 任务名称
    
    Returns:
        bool: 如果任务名称已存在返回 True，否则返回 False
    """
    db = next(get_db())
    try:
        task = db.query(Task).filter(Task.name == task_name).first()
        return task is not None
    finally:
        db.close()


# 初始化数据库表（重建所有表）
init_db(drop_all=False)
