import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pddetectionapp.pddetect import app as pd_app

# 创建主应用
app = FastAPI(title="局部放电检测系统")

# 包含pddetect.py中定义的路由
app.mount("/pd", pd_app)

# 条件性挂载静态文件
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# 主页路由
@app.get("/", response_class=HTMLResponse)
async def root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

# 404页面
@app.get("/404", response_class=HTMLResponse)
async def not_found():
    return FileResponse("404.html")

# 直接运行此文件时启动服务器
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
