# 电脑端/复盘端

## 功能
- **视频解析**：将象棋对局视频解析为PGN格式
- **Stockfish分析**：使用Stockfish引擎分析棋局，生成评估报告
- **网页复盘**：生成仿chess.com风格的网页复盘界面

## 依赖
- Python 3.6+
- OpenCV (用于视频处理)
- python-chess (用于棋盘和走棋处理)
- stockfish (国际象棋引擎)
- jinja2 (用于网页模板渲染)

## 安装
```bash
pip install -r requirements_computer.txt
```

## 下载Stockfish引擎
1. 从官方网站下载Stockfish引擎：https://stockfishchess.org/download/
2. 将下载的可执行文件重命名为"stockfish"并放在项目根目录

## 使用
```bash
python computer_analysis.py <视频文件路径>
```

## 输出
- PGN文件：记录棋局的走棋序列
- 分析报告：包含每一步的评估值和深度
- 网页复盘：交互式的网页复盘界面