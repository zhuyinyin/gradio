from services.training_service import TrainingManager
from services.task_monitor import TaskMonitor
from ui.interface import create_ui
import threading
import signal
import sys

def signal_handler(signum, frame):
    """处理退出信号"""
    print("\n正在关闭应用...")
    sys.exit(0)

class Application:
    def __init__(self):
        self.training_manager = TrainingManager()
        self.task_monitor = TaskMonitor()
        self.monitor_thread = None
        self._running = True
        
        # 设置信号处理
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def start_monitor(self):
        """启动监控线程"""
        def monitor_loop():
            import asyncio
            # 为监控线程创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 运行监控任务
                loop.run_until_complete(self.task_monitor.start_monitoring())
            except Exception as e:
                print(f"监控任务出错: {str(e)}")
            finally:
                loop.close()

        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()

    def start(self):
        """启动应用"""
        try:
            # 启动监控线程
            print("启动监控线程...")
            self.start_monitor()
            
            # 创建并启动 Gradio 界面
            print("启动 Gradio 界面...")
            demo = create_ui(self.training_manager)
            demo.queue()  # 移除 concurrency_count 参数
            demo.launch(
                server_name="0.0.0.0",      # 监听所有网络接口
                server_port=5000,           # 服务端口
                share=False,                # 禁用 Gradio 公共链接分享功能
                show_error=True,            # 在界面上显示详细错误信息
                show_api=False,             # 禁用 API 文档页面
                max_threads=10,             # 设置最大线程数
                auth=None                   # 不使用认证
            )

        except Exception as e:
            print(f"应用启动错误: {str(e)}")
        finally:
            self._running = False

def main():
    """主程序入口"""
    app = Application()
    app.start()

if __name__ == "__main__":
    main()
