import gradio as gr
from config import Config
from pg_db import get_task_list, get_db, Task
import os
from PIL import Image
import asyncio
import nest_asyncio
from sqlalchemy.orm import Session


def create_ui(training_manager):
    """创建 Gradio 界面"""
    with gr.Blocks() as demo:
        # 使用 Tabs 替代手动页面切换
        with gr.Tabs() as tabs:
            # 主页 Tab
            with gr.Tab("主页"):
                with gr.Row():
                    # 左侧参数设置
                    with gr.Column(scale=1):
                        gr.Markdown("## 参数设置")
                        model_dropdown = gr.Dropdown(
                            choices=["AI Toolkit", "Fux", "F.1_dev-fp8"],
                            label="模型选择",
                            value="AI Toolkit"
                        )
                        job_name = gr.Textbox(
                            label="任务名称",
                            placeholder="请输入不重复的任务名称"
                        )
                        
                        # 使用 Accordion ���钮
                        with gr.Accordion("高级参数设置", open=False) as advanced_settings:
                            advanced_inputs = {}
                            for param, value in Config.ADVANCED_SETTINGS.items():
                                if isinstance(value, bool):
                                    advanced_inputs[param] = gr.Checkbox(
                                        label=param,
                                        value=value
                                    )
                                elif isinstance(value, (int, float)):
                                    advanced_inputs[param] = gr.Number(
                                        label=param,
                                        value=value
                                    )
                                else:
                                    advanced_inputs[param] = gr.Textbox(
                                        label=param,
                                        value=str(value)
                                    )

                    # 右侧上传区域
                    with gr.Column(scale=2):
                        gr.Markdown("## 图片上传与训练")
                        with gr.Row():
                            image_upload = gr.File(
                                label="上传文件",
                                file_types=["image", "yaml", "yml"],
                                file_count="multiple",
                                type="filepath",
                                height=100,
                                scale=1,
                                elem_classes="file-upload",
                                interactive=True
                            )
                        
                        with gr.Row():
                            image_preview = gr.Gallery(
                                label="图片预览",
                                columns=[2, 3],
                                height=300,
                                show_label=True,
                                preview=True,
                                allow_preview=True,
                                show_download_button=True,
                                object_fit="contain",
                                elem_classes="image-preview"
                            )
                        
                        with gr.Row():
                            start_training_btn = gr.Button(
                                "提交训练任务",
                                variant="primary",  # 使用主要样式
                                size="lg",         # ��尺寸按钮
                                scale=1
                            )
                        with gr.Row():
                            training_result = gr.Textbox(
                                label="训练结果",
                                interactive=False,
                                show_copy_button=True,
                                scale=1
                            )

            # 任务列表 Tab
            with gr.Tab("训练任务表"):
                task_list_data = get_task_list()
                task_list_output = gr.Dataframe(
                    value=task_list_data["data"],
                    headers=task_list_data["headers"],
                    interactive=True,
                    wrap=True,
                    height=400,
                    # column_config={
                    #     "ID": {"width": 80},
                    #     "Name": {"width": 200},
                    #     "Status": {"width": 120},
                    #     "Results": {"width": 120},
                    #     "Created": {"width": 180},
                    #     "Updated": {"width": 180}
                    # }
                )

                # 结果图片展示
                with gr.Group(visible=False) as results_gallery_box:
                    results_gallery = gr.Gallery(
                        label="训练结果图片",
                        columns=[2, 3, 4],
                        height="auto",
                        preview=True,
                        show_share_button=True,
                        allow_preview=True
                    )
                    close_gallery_btn = gr.Button("关闭")

        # 图片处理函数
        def process_images(files):
            """处理上传的图片"""
            try:
                if not files:
                    return gr.update(value=None)
                
                # 过滤并处理图片文件
                image_files = []
                
                for file in files:
                    if isinstance(file, str):  # 如果是文件路径
                        if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                            image_files.append(file)
                    else:  # 如果是文件对象
                        if file.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                            image_files.append(file.name)
                
                print(f"找到 {len(image_files)} 个图片文件")
                return gr.update(value=image_files if image_files else None)
                
            except Exception as e:
                print(f"图片处理出错: {str(e)}")
                import traceback
                traceback.print_exc()
                return gr.update(value=None)

        def view_task_results(evt: gr.SelectData):
            """查看任务结果"""
            try:
                if evt.index[1] != 3:  # Results 列索引
                    return [gr.update(visible=False), None]
                
                task_id = int(evt.value[0])    # ID 在第一列
                result_text = evt.value[3]     # Results 在第四列
                
                if not result_text.startswith("✅"):
                    return [gr.update(visible=False), None]

                db = next(get_db())
                try:
                    task = db.query(Task).filter(Task.id == task_id).first()
                    if task and task.result_images:
                        image_urls = [img["url"] for img in task.result_images]
                        return [gr.update(visible=True), image_urls]
                finally:
                    db.close()
            except Exception as e:
                print(f"处理任务结果时出错: {str(e)}")
            return [gr.update(visible=False), None]

        # 事件处理函数
        async def submit_training(*args):
            """提交训练任务"""
            try:
                print("开始处理训练提交...")
                print(f"接收到的参数: {args}")
                
                model, name, files, *advanced_args = args
                
                if not files:
                    return gr.update(value="请上传文件")
                if not name:
                    return gr.update(value="请输入任务名称")

                print(f"模型: {model}, 任务名: {name}, 文件数: {len(files) if files else 0}")

                # 使用 nest_asyncio 确保异步调用正常工作
                nest_asyncio.apply()
                
                # 调用训练管理器提交任务
                result = await training_manager.submit_training(
                    model, name, files, *advanced_args
                )
                
                print(f"训练任务提交结果: {result}")
                return gr.update(value=result)
                
            except Exception as e:
                print(f"提交训练失败: {str(e)}")
                import traceback
                traceback.print_exc()
                return gr.update(value=f"提交失败: {str(e)}")

        # 事件绑定
        image_upload.change(
            fn=process_images,
            inputs=image_upload,
            outputs=image_preview,
            show_progress=False,
            api_name="process_images",
            concurrency_limit=5  # 设置并发限制
        )

        task_list_output.select(
            fn=view_task_results,
            outputs=[results_gallery_box, results_gallery],
            concurrency_limit=3  # 设置并发限制
        )

        close_gallery_btn.click(
            fn=lambda: [gr.update(visible=False), None],
            outputs=[results_gallery_box, results_gallery],
            concurrency_limit=1  # 设置并发限制
        )

        start_training_btn.click(
            fn=submit_training,
            inputs=[
                model_dropdown,
                job_name,
                image_upload
            ] + list(advanced_inputs.values()),
            outputs=training_result,
            api_name="submit_training",
            show_progress=True,
            queue=True,
            concurrency_limit=1  # 设置并发限制
        )

    return demo 