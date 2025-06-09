def get_data_storage_method(t):
    # 定义t值与数据存储方式和单位大小的映射
    storage_methods = {
        2: ("uint8", 1),
        3: ("int16", 2),
        4: ("int32", 4),
        5: ("int64", 8),
        6: ("float", 4),
        7: ("doulbe", 8),
    }
    d, k = storage_methods[int.from_bytes(t, "little")]
    return k


def create_hf_prpd_sampledata_table(connection, table_name, m):
    columns_sql = ", ".join([f"`{i}` INT" for i in range(1, m + 1)])
    create_table_sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` (id INT AUTO_INCREMENT PRIMARY KEY, {columns_sql});"
    with connection.cursor() as cursor:
        cursor.execute(create_table_sql)
    connection.commit()


def insert_hf_prpd_sampledata_to_db(connection, table_name, columns_sql, parsed_data):
    cursor = connection.cursor()
    insert_query = f"INSERT INTO `{table_name}` ({columns_sql}) VALUES (%s);"
    cursor.executemany(insert_query, [(val,) for val in parsed_data])
    connection.commit()
