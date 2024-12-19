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
    RUNNING = "running"     # 运行中
    COMPLETED = "completed" # 已完成
    FAILED = "failed"       # 失败

class Task(Base):
    """任务模型类"""
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, index=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, index=True)
    config = Column(JSON, nullable=False)
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
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

def get_task_list():
    """查询数据库中的任务并返回"""
    db = next(get_db())
    try:
        tasks = db.query(Task).all()
        task_list = []
        for task in tasks:
            task_list.append({
                "ID": task.id,
                "Name": task.name,
                "Status": task.status.value,
                "Created": task.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "Updated": task.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        return pd.DataFrame(task_list)
    finally:
        db.close()

def init_db(drop_all=False):
    """初始化数据库
    :param drop_all: 是否删除所有表并重新创建
    """
    if drop_all:
        Base.metadata.drop_all(engine)
    
    # 只创建不存在的表
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

# 初始化数据库表（不删除现有数据）
init_db(drop_all=False)
