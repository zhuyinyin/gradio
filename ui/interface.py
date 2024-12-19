import gradio as gr
from config import Config
from pg_db import get_task_list
import os
from PIL import Image
import asyncio
import nest_asyncio

def create_ui(training_manager):
    """创建 Gradio 界面"""
    with gr.Blocks() as demo:
        with gr.Box():
            # 确保按钮在右边
            with gr.Row():
                with gr.Column(min_width=100):  # 放置第一个按钮
                    home_btn = gr.Button("主页")
                with gr.Column(min_width=200):  # 放置第二个按钮
                    training_result_btn = gr.Button("训练任务表")
                gr.Column(scale=20)  # 中间的占位

        with gr.Box().style(full_width=True) as home_page:
            with gr.Row() as pyrows:
                pyrows.style(full_width=True)
                # 左侧边栏
                with gr.Column(scale=1):
                    gr.Markdown("## 参数设置")

                    model_dropdown = gr.Dropdown(["Model A", "Model B", "Model C"], label="模型选择")
                    job_name = gr.Textbox(label="任务名称")
                    advanced_settings_btn = gr.Button("高级参数设置")

                    # 高级设置弹窗
                    with gr.Box(visible=False) as advanced_settings:
                        advanced_inputs = {}
                        with gr.Row():
                            for param, value in Config.ADVANCED_SETTINGS.items():
                                if isinstance(value, bool):
                                    f1 = gr.Checkbox(label=param, value=value)
                                    advanced_inputs[param] = f1
                                elif isinstance(value, (int, float)):
                                    f2 = gr.Number(label=param, value=value)
                                    advanced_inputs[param] = f2
                                else:
                                    f3 = gr.Textbox(value=str(value), label=param)
                                    advanced_inputs[param] = f3

                # 右侧边栏
                with gr.Column(scale=2):
                    gr.Markdown("## 图片上传与训练")

                    image_upload = gr.File(label="上传文件", file_types=['file'], file_count="multiple")
                    image_preview = gr.Gallery(label="图片预览", elem_id="image-gallery")
                    start_training_btn = gr.Button("提交训练任务")

                    # 训练结果
                    training_result = gr.Textbox(label="训练结果", interactive=False)

        # 任务表页面
        with gr.Box(visible=False) as training_page:
            gr.Markdown("## 训练任务列表")
            task_list_output = gr.DataFrame(get_task_list(), label="任务列表")

        # 使用 gr.State() 来存储当前可见状态
        visibility_state = gr.State(False)

        # 回调函数：点击按钮切换界面
        def switch_page_and_update_tasks():
            """切换到任务列表页面"""
            task_list = get_task_list()  # 获取最新的任务列表
            return gr.update(visible=False), gr.update(visible=True), task_list

        def switch_tohome():
            """切换到主页面"""
            return gr.update(visible=True), gr.update(visible=False)

        def toggle_advanced_settings(current_visibility):
            """切换高级设置的可见性"""
            return gr.update(visible=not current_visibility), not current_visibility

        def process_images(files):
            """处理上传的图片并返回适用于 Gradio 预览的格式"""
            images = []
            for file in files:
                file_extension = os.path.splitext(file.name)[-1].lower()
                if file_extension in Config.VALID_IMAGE_EXTENSIONS:
                    try:
                        img = Image.open(file.name)
                        img = img.convert("RGB")
                        images.append(img)
                    except Exception as e:
                        print(f"处理文件 {file.name} 时出错: {e}")
                        continue
            return images

        async def _submit_training(*args):
            """异步提交训练"""
            return await training_manager.submit_training(*args)

        def submit_training(*args):
            """同步包装函数"""
            nest_asyncio.apply()
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(_submit_training(*args))

        start_training_btn.click(
            fn=submit_training,
            inputs=[model_dropdown, job_name, image_upload] + list(advanced_inputs.values()),
            outputs=training_result
        )

        # 事件绑定
        home_btn.click(
            switch_tohome,
            outputs=[home_page, training_page]
        )

        training_result_btn.click(
            switch_page_and_update_tasks,
            outputs=[home_page, training_page, task_list_output]
        )

        advanced_settings_btn.click(
            toggle_advanced_settings,
            inputs=visibility_state,
            outputs=[advanced_settings, visibility_state]
        )

        image_upload.change(
            fn=process_images,
            inputs=image_upload,
            outputs=image_preview
        )

    return demo 