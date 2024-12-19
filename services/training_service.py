import yaml
from PIL import Image
from io import BytesIO
import os
from config import Config
from pg_db import Task, TaskStatus, get_db
import aiohttp
import json

class TrainingManager:
    """训练管理类"""
    def __init__(self):
        self.session = None

    async def init_session(self):
        """初始化会话"""
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def submit_training(self, *args):
        """提交训练任务"""
        if len(args) < 3:
            return "参数不足"
            
        model, job_name, images = args[:3]
        advanced_params = args[3:]

        if not images:
            return "请上传至少一张图片来开始训练。"

        try:
            if self.session is None:
                await self.init_session()

            yaml_config = None
            files_to_send = []

            # 处理上传的文件
            for image in images:
                file_extension = os.path.splitext(image.name)[-1].lower()
                
                if file_extension in Config.VALID_CONFIG_EXTENSIONS:
                    # 读取并处理 YAML
                    with open(image.name, 'r') as f:
                        yaml_config = yaml.safe_load(f)
                        yaml_config["config"]["name"] = job_name
                    
                    # 更新配置
                    yaml_config = self._update_yaml(
                        dict(zip(Config.ADVANCED_SETTINGS.keys(), advanced_params)), 
                        Config.ADVANCED_SETTINGS, 
                        yaml_config
                    )
                    
                    # 将更新后的 YAML 转换为 BytesIO
                    yaml_content = yaml.dump(yaml_config).encode('utf-8')
                    byte_io = BytesIO(yaml_content)
                    byte_io.seek(0)
                    files_to_send.append(('files', (image.name, byte_io, 'text/yaml')))

                elif file_extension in Config.VALID_IMAGE_EXTENSIONS:
                    with open(image.name, 'rb') as f:
                        byte_io = BytesIO(f.read())
                        byte_io.seek(0)
                        files_to_send.append(('files', (image.name, byte_io, 'image/png')))

            if not yaml_config:
                return "请先上传一个 YAML 配置文件。"

            # 创建 FormData
            form = aiohttp.FormData()
            for field_name, file_tuple in files_to_send:
                form.add_field(field_name,
                             file_tuple[1],
                             filename=file_tuple[0],
                             content_type=file_tuple[2])

            # 提交任务
            url = f"{Config.TOOLKIT_URL}/put_jobs/"
            async with self.session.post(
                url,
                data=form,
                timeout=Config.REQUEST_TIMEOUT
            ) as response:
                if response.status == 200:
                    return await self._create_task(job_name, yaml_config)
                else:
                    response_text = await response.text()
                    return f"任务提交失败: {response_text}"

        except Exception as e:
            print(f"提交任务时出错: {str(e)}")
            return f"提交任务失败: {str(e)}"
        finally:
            # 关闭所有 BytesIO 对象
            for _, file_tuple in files_to_send:
                file_tuple[1].close()

    @staticmethod
    def _update_yaml(args, defaults, config):
        """更新 YAML 配置"""
        options = {
            "save": {},
            "train": {}
        }

        for key, value in defaults.items():
            if key in args:
                if key.startswith('train_'):
                    options["train"][key[6:]] = args[key]
                elif key.startswith('save_'):
                    options["save"][key[5:]] = args[key]

        config["config"]["process"][0]["train"].update(options["train"])
        config["config"]["process"][0]["save"].update(options["save"])
        return config

    @staticmethod
    async def _create_task(job_name, config):
        """创建任务记录"""
        db = next(get_db())
        try:
            task = Task(
                name=job_name,
                status=TaskStatus.PENDING,
                config=config
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return f"任务 {job_name} 已成功提交，任务 ID: {task.id}"
        finally:
            db.close() 