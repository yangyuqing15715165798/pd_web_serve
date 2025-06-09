# your_app/consumers.py
import struct
import pandas as pd
import json
from channels.generic.websocket import AsyncWebsocketConsumer
import mysql.connector
import re
from mysql.connector import Error
from .mysql_connect import DatabaseConnection
from .multimaps import High_frequency_map, Ultra_sonic_map, Transient_ground_voltage

# 打开文件并加载JSON数据
with open("package.json", "r") as file:
    db_config = json.load(file)["database"]


class MyConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_buffer = bytearray()  # 初始化一个字节数组作为数据缓冲区
        self.filename = None

    async def connect(self):  # 当WebSocket连接建立时，该方法将被调用
        await self.accept()

    async def disconnect(self, close_code):  # 当WebSocket连接关闭时，该方法将被调用
        pass

    async def receive(self, text_data=None, bytes_data=None):
        # 当接收到WebSocket消息时，该方法将被调用
        if text_data:
            # 处理文本数据
            await self.handle_text_data(text_data)
        elif bytes_data:
            # 处理字节数据
            await self.handle_bytes_data(bytes_data)

    async def handle_text_data(self, text_data):
        if text_data == "END_OF_DATA":
            print("此数据文件数据接收完成")
            await self.process_complete_data(self.data_buffer)
            self.data_buffer = bytearray()  # 重置缓冲区
        elif text_data == "SEND_NEW_DATA":
            print("准备接收新的数据文件")
            self.data_buffer = bytearray()  # 初始化一个字节数组作为缓冲区域
        else:
            try:
                # 尝试解析JSON数据
                data = json.loads(text_data)
                # 检查是否包含特定的键
                if "file_name" in data:
                    self.filename = data["file_name"]
                    print(f"文件名为: {self.filename}")
                # else:
                #     print("JSON数据不包含'name of file'键")
            except json.JSONDecodeError:
                # 处理普通文本数据
                print("接收到文本数据:", text_data)

    async def handle_bytes_data(self, bytes_data):
        # 处理接收到的字节数据
        print("收到字节数据")
        print("字节数据的字节数:", len(bytes_data))

        self.data_buffer.extend(bytes_data)
        # await save_head_file_info_mysql(self, bytes_data)

        # await self.send(">>>>>> 服务器端已收到数据 <<<<<<")

    async def process_complete_data(self, data):
        print("处理完整的数据，数据大小:", len(data))
        # 解析头部信息
        map_quantity = int.from_bytes(data[286:288], "little")  # 图谱数量
        print("图谱数量：", map_quantity)
        # 初始化指针，跳过头部
        pointer = 512
        head_file_data = data[:pointer]
        await save_head_file_info_mysql(self, head_file_data)  # 保存头文件信息
        # 实例化High_frequency_map对象
        HF_map = High_frequency_map()
        US_map = Ultra_sonic_map()
        TEV_map = Transient_ground_voltage()
        # 循环解析每个图谱数据
        for _ in range(map_quantity):
            if pointer + 4 > len(data):
                raise ValueError("数据长度不足以包含图谱大小信息")

            # 读取图谱类型
            map_type = data[pointer]
            print("图谱类型:", hex(map_type))

            # 读取图谱大小
            map_size = int.from_bytes(data[pointer + 1 : pointer + 5], "little")

            if pointer + map_size > len(data):
                raise ValueError("数据长度不足以包含完整的图谱数据")

            # 读取图谱数据
            map_data = data[pointer : pointer + map_size]
            pointer += map_size  # 移动指针
            # 根据图谱类型处理数据
            if map_type == 0x11:
                # 处理高频PRPD图
                await HF_map.process_hf_prpd_map(self.filename, map_data)
            elif map_type == 0x12:
                # 处理高频PRPS图
                await HF_map.process_hf_prps_map(self.filename, map_data)
            elif map_type == 0x13:
                # 处理高频脉冲波形图
                await HF_map.process_hf_pulse_waveform_map(self.filename, map_data)
            elif map_type == 0x31:
                # 处理超声特征图
                await US_map.process_us_features_map(self.filename, map_data)
            elif map_type == 0x32:
                # 处理超声相位图
                await US_map.process_us_phase_map(self.filename, map_data)
            elif map_type == 0x33:
                # 处理超声脉冲图
                await US_map.process_us_pulse_map(self.filename, map_data)
            elif map_type == 0x34:
                # 处理超声波形图
                await US_map.process_us_waveform_map(self.filename, map_data)
            else:
                print("未知的图谱类型")

        print("所有图谱数据解析完毕")


async def save_head_file_info_mysql(self, data):
    print("将头文件信息数据存到mysql表里")
    table_name = "head_file_info"
    try:
        with DatabaseConnection() as db_conn:  # 连接数据库
            if db_conn.is_connected():
                cursor = db_conn.cursor()
                # 按照JSON定义分割数据
                with open("websocketapp/HEADFILE.json", "r") as file:
                    table_structure = json.load(file)
                columns = ["file_name"]
                insert_data = [self.filename]
                for column, attrs in table_structure["HEAD_FILE"].items():
                    # print("column值为{}".format(column))
                    pos_left = attrs["index"][0]
                    pos_right = attrs["index"][1]
                    byte_data = data[pos_left : pos_right + 1]
                    # print(byte_data)
                    if column in ["version_num", "instrument_version_number"]:
                        # 版本号转化
                        version_parts = [str(int(b)) for b in byte_data]
                        version_str = ".".join(version_parts)
                        columns.append(column)
                        insert_data.append(version_str)
                        # print(version_str)
                    elif attrs["type"] == "VARCHAR":
                        coding = attrs.get("coding", "UTF-8")  # 假设默认编码为UTF-8
                        try:
                            if coding == "UNICODE":
                                # 使用UTF-8解码
                                try:
                                    decoded_string = byte_data.decode("utf-16")
                                    columns.append(column)
                                    insert_data.append(decoded_string)
                                except UnicodeDecodeError:
                                    decoded_string = "解码错误"
                            elif coding == "ASCII":
                                try:
                                    decoded_string = byte_data.decode("ascii")
                                    columns.append(column)
                                    insert_data.append(decoded_string)
                                except UnicodeDecodeError:
                                    decoded_string = "解码错误"
                            else:
                                # 如果没有特定的编码方式，直接转换成字符串
                                try:
                                    decoded_string = byte_data.decode()  # 默认使用UTF-8解码
                                except UnicodeDecodeError:
                                    decoded_string = "解码错误"
                        except UnicodeDecodeError:
                            decoded_string = "解码错误"
                    elif attrs["type"] == "FLOAT":
                        float_num = struct.unpack("f", byte_data)[0]
                        # print(float_num)
                        columns.append(column)
                        insert_data.append(float_num)
                    elif attrs["type"] in ["INT", "BIGINT"]:
                        int_num_small = int.from_bytes(byte_data, "little")
                        # print(int_num_small)
                        columns.append(column)
                        insert_data.append(int_num_small)
                    else:
                        print("数据类型存在错误")
                for i, value in enumerate(insert_data):
                    if pd.isna(value):
                        insert_data[i] = None  # 将NaN转换为None，这在SQL中对应于NULL
                # 构建插入数据的SQL语句
                insert_sql = f"INSERT INTO {table_name} ({','.join(columns)})VALUES({','.join(['%s']*len(columns))})"
                # 执行一次性插入操作
                cursor.execute(insert_sql, insert_data)

            db_conn.commit()
            print("HEAD_FILE_INFO inserted successfully")
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")



async def copy_and_increment_last_number(connection, table_name, columns_to_increment):
    try:
        # 查询上一行数据
        select_query = f"SELECT * FROM {table_name} ORDER BY CAST(SUBSTRING_INDEX(id, '-', -1) AS UNSIGNED) DESC LIMIT 1;"
        cursor = connection.cursor(dictionary=True)
        cursor.execute(select_query)
        previous_row = cursor.fetchone()

        if previous_row:
            # 获取上一行的所有列的数据
            original_data = {key: previous_row[key] for key in previous_row}

            # 对指定列进行增量操作
            for column in columns_to_increment:
                if (
                    column in original_data
                    and isinstance(original_data[column], str)
                    and re.search(r"-(\d+)$", original_data[column])
                ):
                    original_number = int(
                        re.search(r"-(\d+)$", original_data[column]).group(1)
                    )
                    new_number = original_number + 1
                    original_data[column] = re.sub(
                        r"-(\d+)$", f"-{new_number}", original_data[column]
                    )

            # 插入新行
            insert_query = f"INSERT INTO {table_name} ({', '.join(original_data.keys())}) VALUES ({', '.join(['%s'] * len(original_data))})"
            cursor.execute(insert_query, tuple(original_data.values()))
            connection.commit()

            print("成功复制并插入新行！")

    except Exception as e:
        print(f"发生错误：{str(e)}")

    finally:
        cursor.close()
