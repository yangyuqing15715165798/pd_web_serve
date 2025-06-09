import json
import websockets


class WsClient:
    def __init__(self, url) -> None:
        self.url = url  # url是websocket服务器的地址
        self.ws = None  # websocket object
        self.initial_files_sent = False  # 新增标志位

    async def _connect(self, url):  # 私有异步方法
        """
        connect with given websocket 建立到给定URL的websocket连接
        effective in handler function
        """

        try:
            # async with websockets.connect(url) as websocket:
            self.ws = await websockets.connect(
                url
            )  # 异步函数用于建立连接。连接成功后，self.ws属性被设置为WebSocket连接对象。
            print("connect successfully")
            # return websocket
        except websockets.exceptions.InvalidHandshake as e:
            print("handshaking error:", e)

    async def _send(self, data):
        """
        define text sending fun 发送文本信息
        """
        if isinstance(data, dict):
            data = json.dumps(data)  # 将json格式数据转成str

        elif isinstance(data, bytes):
            # 字节数据，直接发送
            pass
        elif isinstance(data, str):
            # 字符串数据，直接发送
            pass
        else:
            print("无效的数据类型")
        if self.ws is not None:
            await self.ws.send(data)
        else:
            print("WebSocket connection is not established")
            # 可选：尝试重新连接或处理错误
        # result = await self.ws.recv()
        # print("sending message:", result)

    async def _onmessage(self):
        """
        接收来自WebSocket服务器的信息
        :return:
        """
        message = await self.ws.recv()  # 异步调用等待并接收来自服务器的消息
        return message

    async def handler(self):
        """
        公开的异步方法，是客户端的主要处理器
        :return:
        """
        await self._connect(self.url)  # 调用 _connect 方法来建立连接
        if self.ws is not None:
            await self._send(
                "Client and server connect successfully"
            )  # 调用 _send 方法来发送一条初始消息（"connect successfully"）
            try:
                while True:  # 无线循环
                    message = (
                        await self._onmessage()
                    )  # 不断调用 _onmessage 方法接收来自服务器的消息，并打印这些消息。
                    print("received message:", message)

            except websockets.exceptions.ConnectionClosed:
                print("connection has been closed")
        else:
            print("WebSocket connection not established")

    async def one_handle(self):
        await self._connect(self.url)  # 调用 _connect 方法来建立连接
        if self.ws is not None:
            # await self._send("Client and server once connect successfully")  # 调用 _send 方法来发送一条初始消息（"connect successfully"）
            print("Client and server once connect successfully")

    async def mark_initial_files_sent(self):
        self.initial_files_sent = True
