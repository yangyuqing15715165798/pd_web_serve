# 局部放电检测系统 (FastAPI版)

## 项目简介

本项目是一个基于深度学习的局部放电(PD)检测系统，使用FastAPI作为后端框架，结合WebSocket实现实时数据处理和预测。系统通过LSTM和注意力机制对局部放电数据进行分类，可用于电力设备的预测性维护和故障诊断。

## 技术栈

- **后端框架**: FastAPI
- **深度学习**: PyTorch, LSTM, 注意力机制
- **数据处理**: Pandas, NumPy, Joblib
- **异步处理**: asyncio, WebSocket
- **前端**: HTML, JavaScript
- **部署**: Uvicorn/Gunicorn

## 系统要求

- Python 3.8+
- Node.js 14+ (前端开发可选)
- 操作系统: Windows/Linux/macOS

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/pd_detection_system.git
cd pd_detection_system
```

### 2. 创建虚拟环境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 确认模型文件存在

确保以下模型文件存在于正确位置:
- `pddetectionapp/models/scaler.save`
- `pddetectionapp/models/state_dict_1.pth`
- `pddetectionapp/models/shu.xlsx` (示例数据)

## 运行系统

### 开发环境运行

```bash
# 使用Uvicorn启动服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 生产环境运行

```bash
# 使用Gunicorn (仅Linux/macOS)
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# Windows生产环境
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 系统功能

### 1. 局部放电检测API

- **端点**: `/api/predict`
- **方法**: POST
- **功能**: 接收局部放电数据，返回预测结果
- **示例**:
  ```bash
  curl -X POST "http://localhost:8000/api/predict" \
       -H "Content-Type: application/json" \
       -d '{"data": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]}'
  ```

### 2. 实时数据处理

- **端点**: `/ws`
- **协议**: WebSocket
- **功能**: 建立持久连接，实时接收数据并返回预测结果
- **客户端示例**:
  ```javascript
  const socket = new WebSocket('ws://localhost:8000/ws');
  socket.onmessage = function(event) {
      const data = JSON.parse(event.data);
      console.log('预测结果:', data.prediction);
  };
  socket.send(JSON.stringify({data: [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]}));
  ```

### 3. 后台数据处理

- **端点**: `/api/data/process`
- **方法**: POST
- **功能**: 异步处理大量数据，适用于批量分析
- **示例**:
  ```bash
  curl -X POST "http://localhost:8000/api/data/process" \
       -H "Content-Type: application/json" \
       -d '{"data": [[...], [...], [...]]}'
  ```

## API文档

启动服务后，可通过以下URL访问自动生成的API文档:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 项目结构

```
pd_detection_system/
├── main.py                    # 主入口文件
├── pddetectionapp/            # 深度学习模型和预测功能
│   ├── pddetect.py            # 模型定义和预测函数
│   └── models/                # 预训练模型和数据
│       ├── scaler.save        # 标准化器
│       ├── state_dict_1.pth   # 模型权重
│       └── shu.xlsx           # 示例数据
├── realtime_data/             # 实时数据处理模块
├── static/                    # 静态文件
├── index.html                 # 主页面
├── 404.html                   # 错误页面
├── requirements.txt           # Python依赖
└── README.md                  # 项目说明
```

## 开发指南

### 添加新的API端点

在`main.py`中添加新的路由:

```python
@app.get("/api/status")
async def get_status():
    return {"status": "running"}
```

### 修改模型参数

编辑`pddetectionapp/pddetect.py`中的模型定义:

```python
model = Bi_lstm(input_dim=3, hidden_dim=128, output_size=3)  # 修改隐藏层大小
```

### 自定义WebSocket处理

修改WebSocket处理逻辑:

```python
@app.websocket("/ws/custom")
async def custom_websocket(websocket: WebSocket):
    # 自定义处理逻辑
    pass
```

## 常见问题

1. **Q: 模型加载失败怎么办?**
   A: 确认模型文件路径正确，并检查是否使用了正确的PyTorch版本

2. **Q: WebSocket连接断开?**
   A: 检查网络连接和防火墙设置，确保端口8000开放

3. **Q: 如何调整模型性能?**
   A: 可以修改`pddetect.py`中的模型参数，如隐藏层大小、LSTM层数等

## 部署建议

1. 使用Nginx作为反向代理
2. 配置SSL证书确保安全连接
3. 使用Docker容器化应用
4. 考虑使用Redis进行缓存和消息队列

## 贡献指南

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可证

本项目采用MIT许可证 - 详情见[LICENSE](LICENSE)文件

## 联系方式

- 项目维护者: [您的名字](mailto:your.email@example.com)
- 项目主页: [GitHub仓库地址](https://github.com/yourusername/pd_detection_system)

---

*注: 本文档基于FastAPI迁移版本，与原Django版本的功能保持一致但实现方式有所不同。*


这个项目的工作流程

## 项目工作流程

1. **前端展示程序**：
   - 开发了网页界面，用于显示局部放电的相关图表和数据
   - 使用HTML、JavaScript构建用户界面
   - 可能使用了图表库(如Chart.js、ECharts等)来可视化局部放电数据

2. **实时数据通信**：
   - 前端通过WebSocket与后端建立持久连接
   - 实现了实时数据传输，使前端能够即时显示最新的检测结果
   - 当有新的局部放电数据产生时，后端会立即推送给前端

3. **网络接口设计**：
   - 后端提供了多种API接口，包括RESTful API和WebSocket
   - 数据以JSON格式在前后端之间传输
   - 接口设计考虑了实时性和数据一致性

4. **数据处理流程**：
   - 后端接收传感器或其他来源的原始局部放电数据
   - 使用深度学习模型(LSTM和注意力机制)进行处理和分类
   - 将处理结果返回给前端进行展示

5. **前后端通信方式**：
   - **WebSocket**：用于实时数据传输和更新
   - **HTTP API**：用于非实时数据查询、历史数据分析等

整个系统是一个典型的实时监测应用，前端负责数据可视化和用户交互，后端负责数据处理和模型推理，两者通过网络接口保持通信，确保用户能够实时看到局部放电的检测结果和相关分析。前端展示的图表可能包括波形图、频谱图、趋势图等，帮助工程师监控和分析电力设备的局部放电状况。

在新的FastAPI版本中，这种前后端通信模式得到了保留，但实现方式从Django迁移到了更轻量、性能更好的FastAPI框架，特别适合处理这种需要低延迟响应的实时应用场景。
