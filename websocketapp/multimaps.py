from .mysql_connect import DatabaseConnection
import json
import struct
import pandas as pd
from mysql.connector import Error
from .save_mysql import get_data_storage_method

class High_frequency_map():
    def __init__(self):
        self.data_buffer = bytearray()

    async def process_hf_prpd_map(self, filename, map_data):
        # 处理高频PRPD图的函数
        print("处理高频PRPD图，数据长度:", len(map_data))
        await self.save_hf_prpd_info_mysql(filename, map_data)


    async def process_hf_prps_map(self, filename, map_data):
        # 处理高频PRPS图的函数
        print("处理高频PRPS图，数据长度:", len(map_data))
        await self.save_hf_prps_info_mysql(filename, map_data)


    async def process_hf_pulse_waveform_map(self, filename, map_data):
        # 处理高频PRPS图的函数
        print("处理高频PRPS图，数据长度:", len(map_data))
        await self.save_hf_pulse_waveform_info_mysql(filename, map_data)


    async def save_hf_prpd_info_mysql(self, filename, data):
        print("将prpd数据存到mysql表里")
        table_name = "hf_prpd_info"
        try:
            with DatabaseConnection() as db_conn:
                if db_conn.is_connected():
                    cursor = db_conn.cursor()
                    # 按照JSON定义分割数据
                    with open("websocketapp/HF.json", "r") as file:
                        table_structure = json.load(file)["HF_PRPD"]
                    columns = ["file_name"]
                    insert_data = [filename]
                    for column, attrs in table_structure["Info"].items():
                        # print("column值为{}".format(column))
                        pos_left = attrs["index"][0]
                        pos_right = attrs["index"][1]
                        byte_data = data[pos_left : pos_right + 1]
                        # print(byte_data)
                        if column in ["discharge_type_probability"]:
                            # 放电概率
                            discharge_probabilities = struct.unpack("8B", byte_data)
                            non_zero_dict = {
                                index: value
                                for index, value in enumerate(discharge_probabilities)
                                if value != 0
                            }
                            # 将字典转换为字符串
                            non_zero_str = json.dumps(non_zero_dict)
                            columns.append(column)
                            insert_data.append(non_zero_str)
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

                    # 建立数据表
                    t = data[336:337]  # 存储数据类型t
                    k = get_data_storage_method(t)  # 字节数
                    print("k的值为：{}".format(k))
                    m = int.from_bytes(data[355:359], "little")  # 相位窗数m
                    n = int.from_bytes(data[359:363], "little")  # 量化幅值n
                    sample_table_name = "hf_prpd_sampledata"  # + self.filename
                    columns_sql = ", ".join([f"`col_{i}` INT" for i in range(1, m + 1)])
                    create_table_sql = f"CREATE TABLE IF NOT EXISTS `{sample_table_name}` (id INT AUTO_INCREMENT PRIMARY KEY, FILE_NAME VARCHAR(50), {columns_sql})"
                    cursor.execute(create_table_sql)
                    db_conn.commit()

                    # 数据解析和插入

                    data_start_index = 512  # 假设数据从此索引开始
                    parsed_data = []
                    for _ in range(n):
                        # 读取可变部分
                        variable_part = data[data_start_index : data_start_index + m * k]

                        # 将每两个字节的可变部分转换为整数
                        parsed_data = [
                            int.from_bytes(variable_part[i : i + k], "little")
                            for i in range(0, len(variable_part), k)
                        ]

                        # 更新下一组数据的起始索引
                        data_start_index += k * m

                        columns_sql = ", ".join([f"`col_{i}`" for i in range(1, m + 1)])
                        columns_sql = "file_name, " + columns_sql
                        # 在 parsed_data 中添加 filename 值
                        parsed_data.insert(0, filename)
                        # 修改 INSERT INTO 语句以包含 float_num 和 variable_part_int_list
                        insert_query = f"INSERT INTO `{sample_table_name}` ({columns_sql}) VALUES ({','.join(['%s']*(m+1))})"
                        # 使用 executemany 来执行批量插入
                        cursor.execute(insert_query, parsed_data)
                        db_conn.commit()
                        parsed_data = []  # 重置数据列表

                db_conn.commit()
                print("HF-PRPD inserted successfully")
        except Error as e:
            print(f"Error while connecting to MySQL: {e}")


    async def save_hf_prps_info_mysql(self, filename, data):
        print("将hf-prps数据存到mysql表里")
        table_name = "hf_prps_info"
        try:
            with DatabaseConnection() as db_conn:
                if db_conn.is_connected():
                    cursor = db_conn.cursor()
                    # 按照JSON定义分割数据
                    with open("websocketapp/HF.json", "r") as file:
                        table_structure = json.load(file)["HF_PRPS"]
                    columns = ["file_name"]
                    insert_data = [filename]
                    for column, attrs in table_structure["Info"].items():
                        # print("column值为{}".format(column))
                        pos_left = attrs["index"][0]
                        pos_right = attrs["index"][1]
                        byte_data = data[pos_left : pos_right + 1]
                        # print(byte_data)
                        if column in ["discharge_type_probability"]:
                            # 放电概率
                            discharge_probabilities = struct.unpack("8B", byte_data)
                            non_zero_dict = {
                                index: value
                                for index, value in enumerate(discharge_probabilities)
                                if value != 0
                            }
                            non_zero_str = json.dumps(non_zero_dict)
                            columns.append(column)
                            insert_data.append(non_zero_str)
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
                    print("prps表信息插入成功")

                    # 建表
                    t = data[336:337]  # 存储数据类型t
                    k = get_data_storage_method(t)  # 字节数
                    print("k的值为：{}".format(k))
                    m = int.from_bytes(data[355:359], "little")  # 相位窗数m
                    p = int.from_bytes(data[363:367], "little")  # 工频周期数p

                    sample_table_name = "hf_prps_sampledata"  # + self.filename
                    columns_sql = ", ".join([f"`col_{i}` INT" for i in range(1, m + 1)])
                    create_table_sql = f"CREATE TABLE IF NOT EXISTS `{sample_table_name}` (id INT AUTO_INCREMENT PRIMARY KEY, file_name VARCHAR(50), {columns_sql})"
                    cursor.execute(create_table_sql)
                    db_conn.commit()

                    # 数据解析和插入

                    data_start_index = 512  # 假设数据从此索引开始
                    parsed_data = []
                    for _ in range(p):
                        # 读取可变部分
                        variable_part = data[data_start_index : data_start_index + m * k]

                        # 将每两个字节的可变部分转换为整数
                        parsed_data = [
                            struct.unpack("<f", variable_part[i : i + k])[0]
                            for i in range(0, len(variable_part), k)
                        ]
                        # print(len(parsed_data))
                        # 更新下一组数据的起始索引
                        data_start_index += k * m

                        columns_sql = ", ".join([f"`col_{i}`" for i in range(1, m + 1)])
                        columns_sql = "file_name, " + columns_sql
                        # 在 parsed_data 中添加 filename 值
                        parsed_data.insert(0, filename)
                        # 修改 INSERT INTO 语句以包含 float_num 和 variable_part_int_list
                        insert_query = f"INSERT INTO `{sample_table_name}` ({columns_sql}) VALUES ({','.join(['%s']*(m+1))})"
                        # 使用 executemany 来执行批量插入
                        cursor.execute(insert_query, parsed_data)
                        db_conn.commit()
                        parsed_data = []  # 重置数据列表

                print("HF-PRPS inserted successfully")
                # except:
                #     print("报错")
        except Error as e:
            print(f"Error while connecting to MySQL: {e}")


    async def save_hf_pulse_waveform_info_mysql(self, filename, data):
        print("将hf-pulse-waveform数据存到mysql表里")
        table_name = "hf_pulse_waveform_info"
        try:
            with DatabaseConnection() as db_conn:
                if db_conn.is_connected():
                    cursor = db_conn.cursor()
                    # 按照JSON定义分割数据
                    with open("websocketapp/HF.json", "r") as file:
                        table_structure = json.load(file)["HF_PULSE_WAVEFORM"]
                    columns = ["file_name"]
                    insert_data = [filename]
                    for column, attrs in table_structure["Info"].items():
                        # print("column值为{}".format(column))
                        pos_left = attrs["index"][0]
                        pos_right = attrs["index"][1]
                        byte_data = data[pos_left : pos_right + 1]
                        # print(byte_data)
                        if column in ["discharge_type_probability"]:
                            # 放电概率
                            discharge_probabilities = struct.unpack("8B", byte_data)
                            non_zero_dict = {
                                index: value
                                for index, value in enumerate(discharge_probabilities)
                                if value != 0
                            }
                            non_zero_str = json.dumps(non_zero_dict)
                            columns.append(column)
                            insert_data.append(non_zero_str)
                        elif attrs["type"] == "VARCHAR":
                            coding = attrs.get("coding", "UTF-8")  # 假设默认编码为UTF-8
                            try:
                                if coding == "UNICODE":
                                    # 使用UTF-16解码
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
                            print("column值为{}".format(column))
                            print(byte_data)
                    for i, value in enumerate(insert_data):
                        if pd.isna(value):
                            insert_data[i] = None  # 将NaN转换为None，这在SQL中对应于NULL
                    # 构建插入数据的SQL语句
                    insert_sql = f"INSERT INTO {table_name} ({','.join(columns)})VALUES({','.join(['%s']*len(columns))})"
                    # 执行一次性插入操作
                    cursor.execute(insert_sql, insert_data)
                    db_conn.commit()

                    # 建数据表
                    t = data[336:337]  # 存储数据类型t
                    k = get_data_storage_method(t)  # 字节数
                    print("k的值为：{}".format(k))
                    n = int.from_bytes(data[355:359], "little")  # n数据点数
                    m = int.from_bytes(data[359:363], "little")  # m脉冲个数
                    q = int(n / m)
                    print("q的值为：{}".format(q))
                    sample_table_name = "hf_pulse_waveform_sampledata"  # + self.filename
                    columns_sql = ", ".join([f"`coll_{i}` INT" for i in range(1, q + 1)])
                    create_table_sql = f"CREATE TABLE IF NOT EXISTS `{sample_table_name}` (id INT AUTO_INCREMENT PRIMARY KEY, file_name VARCHAR(50), start_time FLOAT, {columns_sql})"
                    cursor.execute(create_table_sql)
                    db_conn.commit()

                    # 数据解析和插入
                    data_start_index = 512  # 假设数据从此索引开始
                    fixed_size = 4  # 固定字节
                    pulsed_data = []
                    for _ in range(m):
                        # 读取固定部分
                        fixed_part = data[data_start_index : data_start_index + fixed_size]
                        float_num = struct.unpack("<f", fixed_part)[0]
                        # 读取可变部分
                        variable_part = data[
                            data_start_index
                            + fixed_size : data_start_index
                            + fixed_size
                            + k * q
                        ]

                        # 将每两个字节的可变部分转换为整数
                        variable_part_int_list = [
                            struct.unpack("<f", variable_part[i : i + k])[0]
                            for i in range(0, len(variable_part), k)
                        ]

                        # 更新下一组数据的起始索引
                        data_start_index += k * q + fixed_size

                        columns_sql = ", ".join([f"`coll_{i}`" for i in range(1, q + 1)])
                        columns_sql = "file_name, " + columns_sql
                        # 在 parsed_data 中添加 filename 值
                        variable_part_int_list.insert(0, filename)
                        # 修改 INSERT INTO 语句以包含 float_num 和 variable_part_int_list
                        insert_query = f"INSERT INTO `{sample_table_name}` (`start_time`, {columns_sql}) VALUES (%s, {','.join(['%s']*(q+1))})"
                        # 使用 executemany 来执行批量插入
                        cursor.execute(insert_query, [float_num] + variable_part_int_list)
                        db_conn.commit()

            # db_conn.commit()
            print("HF-PULSE-WAVEFORM inserted successfully")
        except Error as e:
            print(f"Error while connecting to MySQL: {e}")

class Ultra_sonic_map():
    def __init__(self):
        self.data_buffer = bytearray()

    async def process_us_features_map(self, filename, map_data):
        # 处理超声特征图的函数
        print("处理超声特征图，数据长度:", len(map_data))
        await self.save_us_features_info_mysql(filename, map_data)  # 保存超声特征图信息到mysql表里

    async def process_us_phase_map(self, filename, map_data):
        # 处理超声相位图的函数
        print("处理超声相位图，数据长度:", len(map_data))
        await self.save_us_phase_info_mysql(filename, map_data) # 保存超声相位图信息到mysql表里
    
    async def process_us_pulse_map(self, filename, map_data):
        # 处理超声脉冲图的函数
        print("处理超声脉冲图，数据长度:", len(map_data))
        await self.save_us_pulse_map_info_mysql(filename, map_data)
    
    async def process_us_waveform_map(self, filename, map_data):
        # 处理超声波形图的函数
        print("处理超声波形图，数据长度:", len(map_data))
        await self.save_us_waveform_map_info_mysql(filename, map_data)
    
    async def save_us_features_info_mysql(self, filename, data):
        print("将us_features数据存到mysql表里")
        table_name = "us_features_info"
        try:
            with DatabaseConnection() as db_conn:
                if db_conn.is_connected():
                    cursor = db_conn.cursor()
                    # 按照JSON定义分割数据
                    with open("websocketapp/US.json", "r") as file:
                        table_structure = json.load(file)["US_FEATURES"]
                    columns = ["file_name"]
                    insert_data = [filename]
                    for column, attrs in table_structure["Info"].items():
                        # print("column值为{}".format(column))
                        pos_left = attrs["index"][0]
                        pos_right = attrs["index"][1]
                        byte_data = data[pos_left : pos_right + 1]
                        # print(byte_data)
                        if column in ["discharge_type_probability"]:
                            # 放电概率
                            discharge_probabilities = struct.unpack("8B", byte_data)
                            non_zero_dict = {
                                index: value
                                for index, value in enumerate(discharge_probabilities)
                                if value != 0
                            }
                            # 将字典转换为字符串
                            non_zero_str = json.dumps(non_zero_dict)
                            columns.append(column)
                            insert_data.append(non_zero_str)
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
                db_conn.commit()
                print("{} inserted successfully".format(table_name))
        except Error as e:
            print(f"Error while connecting to MySQL: {e}")

    async def save_us_phase_info_mysql(self, filename, data):
        table_name = "us_phase_info"
        print("将{}数据存到mysql表里".format(table_name))
        try:
            with DatabaseConnection() as db_conn:
                if db_conn.is_connected():
                    cursor = db_conn.cursor()
                    # 按照JSON定义分割数据
                    with open("websocketapp/US.json", "r") as file:
                        table_structure = json.load(file)["US_PHASE"]
                    columns = ["file_name"]
                    insert_data = [filename]
                    for column, attrs in table_structure["Info"].items():
                        # print("column值为{}".format(column))
                        pos_left = attrs["index"][0]
                        pos_right = attrs["index"][1]
                        byte_data = data[pos_left : pos_right + 1]
                        # print(byte_data)
                        if column in ["discharge_type_probability"]:
                            # 放电概率
                            discharge_probabilities = struct.unpack("8B", byte_data)
                            non_zero_dict = {
                                index: value
                                for index, value in enumerate(discharge_probabilities)
                                if value != 0
                            }
                            # 将字典转换为字符串
                            non_zero_str = json.dumps(non_zero_dict)
                            columns.append(column)
                            insert_data.append(non_zero_str)
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

                    # 建立数据表
                    t = data[336:337]  # 存储数据类型t
                    k = get_data_storage_method(t)  # 字节数
                    print("k的值为：{}".format(k))
                    n = int.from_bytes(data[347:351], "little")  # 数据点个数n,默认是1000
                    sample_table_name = "us_phase_sampledata"  # 
                    columns_sql = "`phase` FLOAT ,`Q` FLOAT"
                    create_table_sql = f"CREATE TABLE IF NOT EXISTS `{sample_table_name}` (id INT AUTO_INCREMENT PRIMARY KEY, FILE_NAME VARCHAR(50), {columns_sql})"
                    cursor.execute(create_table_sql)
                    db_conn.commit()

                    # 数据解析和插入

                    data_start_index = 512  # 假设数据从此索引开始
                    parsed_data = []
                    for _ in range(n):
                        # 读取可变部分
                        variable_part = data[data_start_index : data_start_index + 2 * k]

                        # 将每两个字节的可变部分转换为整数
                        parsed_data = [
                            int.from_bytes(variable_part[i : i + k], "little")
                            for i in range(0, len(variable_part), k)
                        ]

                        # 更新下一组数据的起始索引
                        data_start_index += k * 2

                        columns_sql = ["`phase`",  "`Q`"]
                        columns_sql = "file_name, " + columns_sql
                        # 在 parsed_data 中添加 filename 值
                        parsed_data.insert(0, filename)
                        # 修改 INSERT INTO 语句以包含 float_num 和 variable_part_int_list
                        insert_query = f"INSERT INTO `{sample_table_name}` ({columns_sql}) VALUES ({','.join(['%s']*(2))})"
                        # 使用 executemany 来执行批量插入
                        cursor.execute(insert_query, parsed_data)
                        db_conn.commit()
                        parsed_data = []  # 重置数据列表

                db_conn.commit()
                print("{} inserted successfully".format(table_name))
        except Error as e:
            print(f"Error while connecting to MySQL: {e}")

    async def save_us_pulse_map_info_mysql(self, filename, data):
        table_name = "us_pulse_map_info"
        print("将{}数据存到mysql表里".format(table_name))
        try:
            with DatabaseConnection() as db_conn:
                if db_conn.is_connected():
                    cursor = db_conn.cursor()
                    # 按照JSON定义分割数据
                    with open("websocketapp/US.json", "r") as file:
                        table_structure = json.load(file)["US_PULSE_MAP"]
                    columns = ["file_name"]
                    insert_data = [filename]
                    for column, attrs in table_structure["Info"].items():
                        # print("column值为{}".format(column))
                        pos_left = attrs["index"][0]
                        pos_right = attrs["index"][1]
                        byte_data = data[pos_left : pos_right + 1]

                        if column in ["discharge_type_probability"]:
                            # 放电概率
                            discharge_probabilities = struct.unpack("8B", byte_data)
                            non_zero_dict = {
                                index: value
                                for index, value in enumerate(discharge_probabilities)
                                if value != 0
                            }
                            # 将字典转换为字符串
                            non_zero_str = json.dumps(non_zero_dict)
                            columns.append(column)
                            insert_data.append(non_zero_str)
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

                    # 建立数据表
                    t = data[336:337]  # 存储数据类型t
                    k = get_data_storage_method(t)  # 字节数
                    print("k的值为：{}".format(k))
                    n = int.from_bytes(data[348:352], "little")  # 数据点个数n,默认是1000
                    sample_table_name = "us_pulse_map_sampledata"  # 
                    create_table_sql = f"CREATE TABLE IF NOT EXISTS `{sample_table_name}` (id INT AUTO_INCREMENT PRIMARY KEY, FILE_NAME VARCHAR(50), T FLOAT ,Q FLOAT)"
                    cursor.execute(create_table_sql)
                    db_conn.commit()

                    # 数据解析和插入

                    data_start_index = 512  # 假设数据从此索引开始
                    parsed_data = []
                    for _ in range(n):
                        # 读取可变部分
                        variable_part = data[data_start_index : data_start_index + 2 * k]

                        # 将每两个字节的可变部分转换为整数
                        parsed_data = [
                            int.from_bytes(variable_part[i : i + k], "little")
                            for i in range(0, len(variable_part), k)
                        ]

                        # 更新下一组数据的起始索引
                        data_start_index += k * 2

                        columns_sql = ["`T`",  "`Q`"]
                        columns_sql = "file_name, " + columns_sql
                        # 在 parsed_data 中添加 filename 值
                        parsed_data.insert(0, filename)
                        # 修改 INSERT INTO 语句以包含 float_num 和 variable_part_int_list
                        insert_query = f"INSERT INTO `{sample_table_name}` ({columns_sql}) VALUES ({','.join(['%s']*(2))})"
                        # 使用 executemany 来执行批量插入
                        cursor.execute(insert_query, parsed_data)
                        db_conn.commit()
                        parsed_data = []  # 重置数据列表

                db_conn.commit()
                print("{} inserted successfully".format(table_name))
        except Error as e:
            print(f"Error while connecting to MySQL: {e}")

    async def save_us_waveform_map_info_mysql(self, filename, data):
        table_name = "us_waveform_map_info"
        print("将{}数据存到mysql表里".format(table_name))
        try:
            with DatabaseConnection() as db_conn:
                if db_conn.is_connected():
                    cursor = db_conn.cursor()
                    # 按照JSON定义分割数据
                    with open("websocketapp/US.json", "r") as file:
                        table_structure = json.load(file)["US_WAVEFORM_MAP"]
                    columns = ["file_name"]
                    insert_data = [filename]
                    for column, attrs in table_structure["Info"].items():
                        # print("column值为{}".format(column))
                        pos_left = attrs["index"][0]
                        pos_right = attrs["index"][1]
                        byte_data = data[pos_left : pos_right + 1]
                        # print(byte_data)
                        if column in ["discharge_type_probability"]:
                            # 放电概率
                            discharge_probabilities = struct.unpack("8B", byte_data)
                            non_zero_dict = {
                                index: value
                                for index, value in enumerate(discharge_probabilities)
                                if value != 0
                            }
                            # 将字典转换为字符串
                            non_zero_str = json.dumps(non_zero_dict)
                            columns.append(column)
                            insert_data.append(non_zero_str)
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

                    # 建立数据表
                    t = data[336:337]  # 存储数据类型t
                    k = get_data_storage_method(t)  # 字节数
                    print("k的值为：{}".format(k))
                    n = int.from_bytes(data[347:350], "little")  # 数据电数
                    sample_table_name = "us_waveform_map_sampledata"  # + self.filename
                    create_table_sql = f"CREATE TABLE IF NOT EXISTS `{sample_table_name}` (id INT AUTO_INCREMENT PRIMARY KEY, FILE_NAME VARCHAR(50), Q FLOAT)"
                    cursor.execute(create_table_sql)
                    db_conn.commit()

                    # 数据解析和插入

                    data_start_index = 512  # 假设数据从此索引开始
                    parsed_data = []
                    for _ in range(n):
                        # 读取可变部分
                        variable_part = data[data_start_index : data_start_index + k]

                        # 将每两个字节的可变部分转换为整数
                        parsed_data = [
                            int.from_bytes(variable_part[i : i + k], "little")
                            for i in range(0, len(variable_part), k)
                        ]

                        # 更新下一组数据的起始索引
                        data_start_index += k
                        columns_sql = "file_name, " + "`Q`"
                        # 在 parsed_data 中添加 filename 值
                        parsed_data.insert(0, filename)
                        # 修改 INSERT INTO 语句以包含 float_num 和 variable_part_int_list
                        insert_query = f"INSERT INTO `{sample_table_name}` ({columns_sql}) VALUES ({','.join(['%s']*(2))})"
                        # 使用 executemany 来执行批量插入
                        cursor.execute(insert_query, parsed_data)
                        db_conn.commit()
                        parsed_data = []  # 重置数据列表

                db_conn.commit()
                print("{} inserted successfully".format(table_name))
        except Error as e:
            print(f"Error while connecting to MySQL: {e}")

class Transient_ground_voltage():
    def __init__(self):
        self.data_buffer = bytearray()

    async def process_tev_voltage(self, filename, data):
        # 处理TEV电压的函数
        print("处理TEV电压，数据长度:", len(data))
        await self.save_tev_voltage_info_mysql(filename, data)

    async def save_tev_voltage_info_mysql(self, filename, data):
        print("将tev_voltage数据存到mysql表里")
        table_name = "tev_voltage_info"
        try:
            with DatabaseConnection() as db_conn:
                if db_conn.is_connected():
                    cursor = db_conn.cursor()
                    # 按照JSON定义分割数据
                    with open("websocketapp/TEV.json", "r") as file:
                        table_structure = json.load(file)["TEV_VOLTAGE"]
                    columns = ["file_name"]
                    insert_data = [filename]
                    for column, attrs in table_structure["Info"].items():
                        # print("column值为{}".format(column))
                        pos_left = attrs["index"][0]
                        pos_right = attrs["index"][1]
                        byte_data = data[pos_left : pos_right + 1]
                        # print(byte_data)
                        if column in ["discharge_type_probability"]:
                            # 放电概率
                            discharge_probabilities = struct.unpack("8B", byte_data)
                            non_zero_dict = {
                                index: value
                                for index, value in enumerate(discharge_probabilities)
                                if value != 0
                            }
                            # 将字典转换为字符串
                            non_zero_str = json.dumps(non_zero_dict)
                            columns.append(column)
                            insert_data.append(non_zero_str)
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

                db_conn.commit()
                print("{} inserted successfully".format(table_name))
        except Error as e:
            print(f"Error while connecting to MySQL: {e}")
    