import torch
import joblib
import pandas as pd
import os
import torch.nn as nn
import numpy as np
import torch.nn.functional as F
import asyncio
from fastapi import FastAPI, WebSocket, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer


class Attn(nn.Module):
    def __init__(self, hidden_size, batch_first=True):
        super(Attn, self).__init__()
        self.hidden_size = hidden_size
        self.batch_first = batch_first

        self.weights = nn.Parameter(torch.Tensor(hidden_size, 1))
        stdv = 1.0 / np.sqrt(self.hidden_size)
        for weight in self.weights:
            nn.init.uniform_(weight, -stdv, stdv)

    def forward(self, x):
        if self.batch_first:
            batch_size, seq_size = x.size()[:2]
        else:
            seq_size, batch_size = x.size()[:2]

        weights = torch.bmm(x, self.weights.unsqueeze(0).repeat(batch_size, 1, 1))

        attentions = torch.softmax(F.relu(weights.squeeze()), dim=-1)

        # apply attention weights
        weighted_input = torch.mul(x, attentions.unsqueeze(-1).expand_as(x))

        return torch.sum(weighted_input, axis=1)  # , attentions


# This is NN LSTM Model creation
class Bi_lstm(nn.Module):
    """LSTM循环神经网络"""

    def __init__(self, input_dim, hidden_dim, output_size):
        super(Bi_lstm, self).__init__()
        self.ls1 = nn.LSTM(
            input_size=3,
            hidden_size=32,
            num_layers=1,
            bidirectional=False,
            batch_first=True,
        )
        # self.ls2 = nn.LSTM(input_size=64, hidden_size=32, num_layers=1, bidirectional=False, batch_first=True)
        self.fc1 = nn.Linear(in_features=32, out_features=16)
        self.fc2 = nn.Linear(in_features=16, out_features=output_size)
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()
        self.attention = Attn(32)

    def forward(self, x):
        out, _ = self.ls1(x)
        out = self.attention(out)
        out = self.fc1(out)
        out = self.relu(out)
        out = self.fc2(out)
        # out = self.sigmoid(out)

        return out

    async def predict(self, test_x):
        out, _ = self.ls1(test_x)
        out = self.attention(out)
        out = self.fc1(out)
        out = self.relu(out)
        out = self.fc2(out)
        # out = self.sigmoid(out)
        return out  # .detach().numpy()


async def preprocess_data(new_data, scaler):
    # 应用与训练时相同的标准化
    standardized_data = scaler.transform(new_data)

    return standardized_data


def predict(model, preprocessed_data):
    # 转换为Tensor
    input_tensor = torch.tensor(preprocessed_data, dtype=torch.float32)
    input_tensor = input_tensor.unsqueeze(0)
    # 使用模型进行预测
    # model.eval()
    with torch.no_grad():
        output = model(input_tensor)
        predicted = torch.argmax(output, dim=1)

    return predicted.numpy()


async def PD_detect(new_data):
    # print("Current working directory:", os.getcwd())
    scaler = joblib.load("pddetectionapp/models/scaler.save")

    model = Bi_lstm(input_dim=3, hidden_dim=256, output_size=3)
    model.load_state_dict(
        torch.load(
            "pddetectionapp/models/state_dict_{}.pth".format(1),
            map_location=torch.device("cpu"),
        )
    )

    model.eval()  # 切换到评估模式

    # 假设 new_data 是新的原始数据，scaler 是训练时使用的StandardScaler实例

    preprocessed_data = await preprocess_data(new_data, scaler)

    predictions = predict(model, preprocessed_data)[0]
    # print("预测结果为：{}".format(predictions))
    return predictions


if __name__ == "__main__":
    data = pd.read_excel("pddetectionapp/models/shu.xlsx").values
    PD_detect(data)


app = FastAPI(title="局部放电检测系统")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()
            
            # 处理数据
            if "data" in data:
                # 将数据转换为模型需要的格式
                input_data = np.array(data["data"])
                
                # 使用模型进行预测
                result = await PD_detect(input_data)
                
                # 发送预测结果
                await websocket.send_json({"prediction": int(result)})
    except Exception as e:
        print(f"WebSocket错误: {e}")
    finally:
        # 连接关闭
        print("WebSocket连接关闭")

# 后台任务处理实时数据
async def process_realtime_data(data):
    # 数据处理逻辑
    pass

# API端点
@app.post("/api/data/process")
async def add_data_to_process(data: dict, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_realtime_data, data)
    return {"status": "processing"}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # 验证令牌并返回用户
    user = await validate_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
