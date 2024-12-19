import os

class Config:
    """应用配置类"""
    TOOLKIT_URL = os.getenv('TOOLKIT_URL', 'http://172.25.0.1:7861')
    VALID_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png']
    VALID_CONFIG_EXTENSIONS = ['.yaml', '.yml']
    MONITOR_INTERVAL = 10  # 监控间隔时间（秒）
    REQUEST_TIMEOUT = 30  # 请求超时时间（秒）

    # 高级设置默认值（确保所有数值都是整数）
    ADVANCED_SETTINGS = {
        "save_dtype": "float16",
        "save_save_every": int(1000),
        "save_max_step_saves_to_keep": int(4),
        "train_dtype": "bf16",
        "train_batch_size": int(1),
        "train_ema_config_ema_decay": "0.99",
        "train_ema_config_use_ema": True,
        "train_gradient_accumulation_steps": int(1),
        "train_gradient_checkpointing": True,
        "train_lr": float(0.0004),  # 明确指定为 float
        "train_noise_scheduler": "flowmatch",
        "train_optimizer": "adamw8bit",
        "train_skip_first_sample": True,
        "train_steps": int(2000),
        "train_train_text_encoder": False,
        "train_train_unet": True
    } 