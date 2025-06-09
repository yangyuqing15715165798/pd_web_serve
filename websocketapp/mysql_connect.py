import mysql.connector
from mysql.connector import Error
import json


class DatabaseConnection:
    def __init__(self):
        # 打开文件并加载JSON数据
        with open("package.json", "r") as file:
            db_config = json.load(file)["database"]
        self.host_name = db_config["host_name"]
        self.db_name = db_config["db_name"]
        self.user_name = db_config["user_name"]
        self.user_password = db_config["user_password"]
        self.connection = None

    def __enter__(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host_name,
                database=self.db_name,
                user=self.user_name,
                password=self.user_password,
            )
            return self.connection
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection and self.connection.is_connected():
            self.connection.close()


# 使用示例
db_config = {
    "host_name": "localhost",
    "db_name": "your_db_name",
    "user_name": "your_user_name",
    "user_password": "your_password",
}


with DatabaseConnection() as connection:
    if connection.is_connected():
        # 执行数据库操作
        pass
