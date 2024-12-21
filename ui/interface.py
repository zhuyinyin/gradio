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
    with gr.Blocks(css="""
        .section-header h2 {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #374151;
        }
        .result-gallery {
            margin-top: 0.5rem;
        }
    """) as demo:
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
                        
                        # 使用 Accordion 
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
                                file_types=["image", "yaml", "yml", "txt"],
                                file_count="multiple",
                                type="filepath",
                                height=100,
                                scale=1,
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
                                size="lg",         # 按钮
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
                # 使用 Row 布局，左侧表格，右侧图片
                with gr.Row():
                    # 左侧任务列表表格
                    with gr.Column(scale=2):
                        gr.Markdown("## 训练任务列表", elem_classes="section-header")
                        task_list_data = get_task_list()
                        task_list_output = gr.Dataframe(
                            value=task_list_data["data"],
                            headers=task_list_data["headers"],
                            interactive=False,      # 设置为不可交互
                            wrap=True,             # 允许文本换行
                            height=550,            # 设置高度
                            datatype=[             # 指定每列的数据类型
                                "number",          # ID
                                "str",             # Name
                                "str",             # Status
                                "str",             # Results
                                "str",             # Created
                                "str"              # Updated
                            ],
                            column_widths=[        # 设置列宽
                                "80px",            # ID
                                "200px",           # Name
                                "120px",           # Status
                                "120px",           # Results
                                "180px",           # Created
                                "180px"            # Updated
                            ],
                            row_count=(10, "dynamic"),  # 每页显示10行
                            line_breaks=True,      # 允许换行
                            min_width=160          # 最小宽度
                        )
                    
                    # 右侧图片展示区域
                    with gr.Column(scale=1):
                        gr.Markdown("## 训练结果图片", elem_classes="section-header")
                        results_gallery = gr.Gallery(
                            label="训练结果",            # 移除标签
                            columns=[1, 2],
                            height=550,            # 与表格高度一致
                            preview=True,
                            show_share_button=True,
                            show_download_button=True,
                            allow_preview=True,
                            elem_classes="result-gallery"
                        )

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
                row_index = evt.index[0]    # 行索引
                col_index = evt.index[1]    # 列索引
                print(f"选中行: {row_index}, 列: {col_index}, 值: {evt.value}")
                
                # 从任务列表中获取当前行的数据
                task_list_data = get_task_list()
                try:
                    row_data = task_list_data["data"][row_index]
                except IndexError:
                    print(f"IndexError: 行索引超出范围: {row_index}")
                    return None  # 只返回图片列表
                
                task_id = int(row_data[0])      # ID 在第一列
                result_text = row_data[3]       # Results 在第四列
                
                print(f"任务ID: {task_id}, 结果状态: {result_text}")
                
                if not result_text.startswith("✅"):
                    print("该任务无结果可查看")
                    return None  # 只返回图片列表

                db = next(get_db())
                try:
                    task = db.query(Task).filter(Task.id == task_id).first()
                    if task and task.result_images:
                        image_urls = [img["url"] for img in task.result_images]
                        print(f"找到 {len(image_urls)} 张结果图片")
                        return image_urls  # 只返回图片列表
                finally:
                    db.close()
            except Exception as e:
                print(f"处理任务结果时出错: {str(e)}")
                import traceback
                traceback.print_exc()
            return None  # 只返回图片列表

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

        def refresh_task_list():
            """刷新任务列表"""
            task_list_data = get_task_list()
            return gr.update(
                value=task_list_data["data"],
                headers=task_list_data["headers"]
            )

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
            outputs=results_gallery  # 只更新图片列表
        )

        # close_gallery_btn.click(
        #     fn=lambda: [gr.update(visible=False), None],
        #     outputs=[results_gallery_box, results_gallery]
        # )

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

        demo.load(
            fn=refresh_task_list,
            outputs=task_list_output,
            every=10  # 每10秒刷新一次
        )

    return demo 