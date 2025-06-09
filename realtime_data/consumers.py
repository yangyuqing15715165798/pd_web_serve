import json
from .utils import res_pdData
from channels.generic.websocket import WebsocketConsumer
import time


class Data_Consumer(WebsocketConsumer):
    def connect(self):
        return super().connect()

    def disconnect(self, code):
        return super().disconnect(code)

    def receive(self, text_data=None):
        try:
            data_json = json.loads(text_data)
            if data_json["requester"] == "font-end":
                res_data = res_pdData(data_json["data"])
                time.sleep(1)
                return super().send(res_data)
        except:
            return super().send("data reading failed")
