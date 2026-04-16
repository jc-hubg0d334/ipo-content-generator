#!/bin/bash

set -e

cd "$(dirname "$0")"

if [ ! -d "ipo_ai" ]; then
  echo ">>> 虚拟环境不存在，正在创建..."
  python3 -m venv ipo_ai
fi

echo ">>> 激活虚拟环境..."
source ipo_ai/bin/activate

echo ">>> 安装/检查依赖..."
pip install -r requirements.txt >/dev/null

echo ">>> 启动 IPO Bot..."
python app.py
