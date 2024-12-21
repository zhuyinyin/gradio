import asyncio
from pg_db import Task, TaskStatus, get_db
from config import Config
import json
import logging
import aiohttp
from typing import Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskMonitor:
    """任务监控类"""
    def __init__(self):
        self._running = True
        self.session: Optional[aiohttp.ClientSession] = None

    async def _update_task_status(self, task: Task, new_status: TaskStatus, db) -> None:
        """更新任务状态"""
        if task.status != new_status:
            if new_status == TaskStatus.RUN_BEFORE:
                try:
                    # 从配置中获取 get_files 服务的 URL
                    get_files_url = f"{Config.GET_FILES_URL}/get_file"
                    
                    # 准备请求数据
                    request_data = {
                        "database_url": Config.DATABASE_URL.replace("db", Config.DB_HOST),  # 使用配置中的数据库主机
                        "task_id": task.id,
                        "toolkit_url": Config.TOOLKIT_URL
                    }
                    
                    # 发送 HTTP 请求但不等待响应
                    try:
                        await self.session.post(
                            get_files_url,
                            json=request_data,
                            headers={'Content-Type': 'application/json'},
                            timeout=60
                        )
                        logger.info(f"已发送请求到 get_files 服务处理任务 {task.id}")
                    except Exception as e:
                        logger.error(f"发送请求到 get_files 服务时出错: {str(e)}")
                            
                except Exception as e:
                    logger.error(f"处理 RUN_BEFORE 状态时出错: {str(e)}")
                    # 如果处理过程出错，将任务状态设置为失败
                    task.status = TaskStatus.FAILED
                    db.commit()
                    logger.info(f"任务 {task.name} 状态更新为: {TaskStatus.FAILED.value}")
                    return
            
            # 如果没有错误，正常更新状态
            task.status = new_status
            db.commit()
            logger.info(f"任务 {task.name} 状态更新为: {new_status.value}")

    async def monitor_task(self, task: Task, db) -> None:
        """监控单个任务状态"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            url = f"{Config.TOOLKIT_URL}/get_zip/"
            request_data = json.dumps({"job_name": task.name})
            
            async with self.session.post(
                url,
                data=request_data,
                headers={'Content-Type': 'application/json'},
                timeout=Config.REQUEST_TIMEOUT
            ) as response:
                status_map = {
                    200: TaskStatus.RUN_BEFORE,
                    201: TaskStatus.TRAINING
                }
                new_status = status_map.get(response.status, TaskStatus.FAILED)
                await self._update_task_status(task, new_status, db)
                
        except Exception as e:
            logger.error(f"监控任务 {task.name} 失败: {str(e)}")
            await self._update_task_status(task, TaskStatus.FAILED, db)

    async def start_monitoring(self) -> None:
        """开始监控所有任务"""
        try:
            self.session = aiohttp.ClientSession()
            logger.info("开始监控任务...")
            
            while self._running:
                db = next(get_db())
                try:
                    tasks = db.query(Task).filter(
                        Task.status.in_([TaskStatus.TRAINING, TaskStatus.PENDING])
                    ).limit(10).all()

                    if tasks:
                        # logger.info(f"发现 {len(tasks)} 个待监控任务")
                        await asyncio.gather(
                            *[self.monitor_task(task, db) for task in tasks]
                        )
                    else:
                        logger.info("当前没有需要监控的任务")

                except Exception as e:
                    logger.error(f"监控周期出错: {str(e)}")
                finally:
                    db.close()

                await asyncio.sleep(Config.MONITOR_INTERVAL)

        finally:
            if self.session:
                await self.session.close()
            logger.info("监控任务已停止")

    def stop(self) -> None:
        """停止监控"""
        self._running = False
        logger.info("正在停止任务监控...")