import time
from datetime import datetime
import asyncio
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


async def initial_files_data(folder_path, web_client):  # 初始文件数据
    if web_client.initial_files_sent == False:
        print("********** 指定路径文件夹里已存有数据 **********")
        print("************** 开始发送原有数据 **************")
        for filename in os.listdir(folder_path):  # 文件夹路径下的所有文件名
            file_path = os.path.join(folder_path, filename)  # 所有文件的绝对路径
            if os.path.isfile(file_path):  # 判断文件是否存在
                if file_path.endswith(".dat"):  # 文件名结尾是否为.dat
                    creation_time = os.stat(file_path).st_atime  # 文件的创建时间
                    # 将时间戳转换为可读的日期-时间格式
                    correct_datetime = datetime.fromtimestamp(creation_time).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    await send_file_data(
                        file_path, filename, correct_datetime, web_client
                    )  # 对文件进行发送
            print("原始文件名为:{}".format(filename))
        # print("================ 完成初始数据的发送 ================")
        # await web_client.mark_initial_files_sent()  # 标记初始文件已发送, 更改标志位


async def send_file_data(file_path, file_name, create_time, web_client):
    await web_client._send({"file_name": file_name[:-4]})
    try:
        file_size = os.path.getsize(file_path)
        print("文件的大小:{}".format(file_size))
        chunk_size = 1024 * 1024  # 1MB大小的块
        remaining_size = file_size
        # 发送数据块
        await web_client._send("发送新数据")
        with open(file_path, "rb") as file:
            while remaining_size > 0:
                # 读取数据块
                chunk_data = file.read(min(chunk_size, remaining_size))
                if not chunk_data:
                    break

                # 发送数据块
                await web_client._send(chunk_data)

                # 更新剩余大小
                remaining_size -= len(chunk_data)

        await web_client._send("END_OF_DATA")
        # 发送传输完成的标志位
        # await web_client._send({"end_of_file": 1})  # # 发送一个JSON对象，表示文件传输完成
        print("====== {}数据集已发送，服务器正在接收中 ======".format(file_path))

    except Exception as e:
        print(f"在读取文件 {file_path} 时出现错误: {e}")


class MyHandler(FileSystemEventHandler):
    def __init__(self, webclient, loop):
        self.webclient = webclient  # webclient object
        self.loop = loop

    def on_created(self, event):
        if event.src_path.endswith(".dat"):
            print(f"New data {event.src_path} has been created!")
            print("************* 发送新生成的数据文件 **************")
            # 从完整的文件路径中提取文件名
            file_name = os.path.basename(event.src_path)
            creation_time = os.stat(event.src_path).st_atime  # 文件的创建时间
            # 将时间戳转换为可读的日期-时间格式
            correct_datetime = datetime.fromtimestamp(creation_time).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            asyncio.run_coroutine_threadsafe(
                self.handle_created(event, file_name, correct_datetime),
                self.loop,
            )

    async def handle_created(self, event, file_name, create_time):
        # 检查文件是否准备好读取，如果准备好，则发送文件数据
        try:
            if await self.wait_for_file_ready(event.src_path):
                await send_file_data(
                    event.src_path,
                    file_name,
                    create_time,
                    self.webclient,
                )
            else:
                print(f"文件 {event.src_path} 未准备就绪。")
        except Exception as e:
            print(f"处理文件 {event.src_path} 时出错: {e}")

    async def wait_for_file_ready(self, file_path, timeout=30, check_interval=1):
        """
        异步等待文件准备就绪。

        :param file_path: 文件的路径。
        :param timeout: 等待文件就绪的超时时间（秒）。
        :param check_interval: 检查文件状态的间隔时间（秒）。
        :return: 文件是否就绪。
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not os.path.exists(file_path):
                await asyncio.sleep(check_interval)
                continue

            try:
                with open(file_path, "rb") as file:
                    return True  # 文件已准备就绪
            except IOError:
                # 文件可能正在写入中，稍后重试
                print("文件可能正在写入中，稍后重试")
                await asyncio.sleep(check_interval)

        return False  # 超时，文件未就绪

    # async def on_deleted(self, event):
    #     print(f"{event.src_path} has been deleted!")
    #
    # async def on_modified(self, event):
    #     print(f"{event.src_path} has been modified!")
    #
    # async def on_moved(self, event):
    #     print(f"{event.src_path} was moved to {event.dest_path}")


async def start_monitoring(path, webclient):
    loop = asyncio.get_running_loop()  # 获取主线程的事件循环
    event_handler = MyHandler(webclient, loop)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        await asyncio.Future()
    finally:
        observer.stop()
        observer.join()
