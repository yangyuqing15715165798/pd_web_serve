import asyncio
from modules import WsClient
from utils import initial_files_data, start_monitoring
import argparse
import os

parser = argparse.ArgumentParser(description="客户端发送数据")
parser.add_argument(
    "--dir_path", type=str, default="E:\Project program\dataa", help="需要监视的文件夹路径"
)
URL = "ws://47.104.102.28:8000/chat/"
# URL = "ws://127.0.0.1:8000/chat/"
args = parser.parse_args()


async def main():
    if not os.path.exists(args.dir_path):
        print(f"给定的路径不存在: {args.dir_path}")
        return
    web_client = WsClient(URL)  # 创建 WsClient 类的实例，用于管理 WebSocket 连接

    connected = False
    while not connected:
        try:
            await web_client.one_handle()  # 尝试连接
            connected = True  # 如果连接成功，标记为 True
        except Exception as e:
            print(f"连接失败: {e} 将在 10 秒后重试...")
            await asyncio.sleep(10)  # 等待 10 秒后重试

    await initial_files_data(args.dir_path, web_client)
    # 定义其他异步任务
    await asyncio.gather(
        web_client.handler(), start_monitoring(args.dir_path, web_client)
    )


if __name__ == "__main__":
    print("***********客户端开始运行***********")
    asyncio.run(main())
