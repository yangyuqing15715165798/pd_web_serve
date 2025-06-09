# your_app/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
import mysql.connector
import asyncio
import aiomysql
from .pddetect import PD_detect

# 打开文件并加载JSON数据
with open("package.json", "r") as file:
    db_config = json.load(file)["database"]


class PDConsumer(AsyncWebsocketConsumer):
    async def connect(self):  # 当WebSocket连接建立时，该方法将被调用
        await self.accept()
        connection = await create_connection()
        try:
            await read_mysql(connection)
        finally:
            connection.close()

    async def disconnect(self, close_code):  # 当WebSocket连接关闭时，该方法将被调用
        pass

    async def receive(self, text_data):  # 当接收到WebSocket消息时，该方法将被调用
        pass

        await self.send(">>>>>> 服务器端已收到数据 <<<<<<")

    # 连接数据库的函数


async def create_connection():
    return await aiomysql.connect(
        host=db_config["host_name"],
        user=db_config["user_name"],
        password=db_config["user_password"],
        db=db_config["db_name"],
        loop=asyncio.get_event_loop(),
    )


# 查询数据总行数的函数
async def get_total_rows(connection):
    async with connection.cursor() as cursor:
        await cursor.execute("SELECT COUNT(*) FROM sample_data")
        result = await cursor.fetchone()
    return result[0]


# 读取数据的函数
async def read_data(connection, current_row, batch_size):
    async with connection.cursor() as cursor:
        await cursor.execute(
            f"SELECT max_peak, freq, tim FROM sample_data LIMIT {current_row}, {batch_size}"
        )
        return await cursor.fetchall()


# 实时监测数据表并输出新数据的函数
async def monitor_table(connection, batch_size):
    current_row = 0
    total_rows = await get_total_rows(connection)
    while True:
        new_total_rows = await get_total_rows(connection)
        if new_total_rows >= current_row + batch_size:
            end_row = current_row + batch_size - 1
            rows = await read_data(connection, current_row, batch_size)
            cla_result = await PD_detect(rows)
            await insert_result(connection, current_row, end_row, cla_result)
            current_row += batch_size
        await asyncio.sleep(5)  # 每5秒检查一次


async def insert_result(connection, current_row, end_row, cla_result):
    try:
        async with connection.cursor() as cursor:
            insert_query = "INSERT INTO pd_result (start_index, end_index, detect_result) VALUES (%s, %s, %s)"
            await cursor.execute(insert_query, (current_row, end_row, cla_result))
            await connection.commit()
    except Exception as e:
        print(f"An error occurred: {e}")
        await connection.rollback()
        raise


async def read_mysql(connection):
    batch_size = 100
    await monitor_table(connection, batch_size)
