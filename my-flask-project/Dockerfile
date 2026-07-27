    # 使用 Python 官方轻量级镜像
    FROM python:3.9-slim

    # 设置工作目录
    WORKDIR /app

    # 复制依赖文件
    COPY requirements.txt .

    # 安装依赖
    RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

    # 复制所有代码
    COPY . .

    # 启动命令
    # 云端会自动注入 PORT 环境变量，这里使用 python app.py 启动
    CMD ["python", "app.py"]
