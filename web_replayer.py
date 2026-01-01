#!/usr/bin/env python3
"""
网页复盘模块
功能：生成仿chess.com风格的网页复盘界面
"""

import os
import json
from jinja2 import Template

class WebReplayer:
    def __init__(self):
        self.templates_dir = "templates"
        self.output_dir = "web_replays"
        
        # 创建目录
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 创建HTML模板
        self.create_template()
    
    def create_template(self):
        """创建HTML模板文件"""
        template_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>象棋复盘</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f0f0f0;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            display: flex;
        }
        
        .board-container {
            flex: 1;
            margin-right: 20px;
        }
        
        .board {
            width: 100%;
            max-width: 600px;
            height: 600px;
            background-color: #f0d9b5;
            border: 2px solid #8b4513;
            margin: 0 auto;
        }
        
        .move-list {
            width: 300px;
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            max-height: 600px;
            overflow-y: auto;
        }
        
        .move-item {
            padding: 8px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
        }
        
        .move-item:hover {
            background-color: #f5f5f5;
        }
        
        .move-item.active {
            background-color: #e6f7ff;
            font-weight: bold;
        }
        
        .analysis-panel {
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            margin-top: 20px;
        }
        
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }
        
        .controls {
            text-align: center;
            margin: 20px 0;
        }
        
        button {
            padding: 10px 20px;
            margin: 0 5px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        
        button:hover {
            background-color: #45a049;
        }
    </style>
</head>
<body>
    <h1>象棋复盘</h1>
    
    <div class="container">
        <div class="board-container">
            <div class="board" id="chessBoard">
                <!-- 棋盘将通过JavaScript渲染 -->
            </div>
            
            <div class="controls">
                <button onclick="goToStart()">开始</button>
                <button onclick="goToPrevious()">上一步</button>
                <button onclick="goToNext()">下一步</button>
                <button onclick="goToEnd()">结束</button>
            </div>
            
            <div class="analysis-panel">
                <h3>当前局面分析</h3>
                <div id="currentAnalysis">选择一步棋查看分析</div>
            </div>
        </div>
        
        <div class="move-list">
            <h3>走棋列表</h3>
            <div id="moveList">
                {% for move in moves %}
                <div class="move-item" onclick="selectMove({{ loop.index0 }})">
                    {{ move.move_number }}. {{ move.white }} {% if move.black %}{{ move.black }}{% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
    
    <script>
        // 游戏数据
        const gameData = {{
            moves: moves,
            analysis: analysis
        }};
        
        let currentMoveIndex = 0;
        
        function renderBoard() {
            // 渲染棋盘的逻辑，实际应用中可以使用chess.js和chessboard.js
            const boardElement = document.getElementById('chessBoard');
            boardElement.innerHTML = `<div style="text-align: center; padding: 200px; font-size: 24px;">棋盘渲染区域</div>`;
        }
        
        function updateAnalysis() {
            const analysisElement = document.getElementById('currentAnalysis');
            if (gameData.analysis && gameData.analysis[currentMoveIndex]) {
                const analysis = gameData.analysis[currentMoveIndex];
                analysisElement.innerHTML = `
                    <p>评估值: ${analysis.evaluation}</p>
                    <p>分析深度: ${analysis.depth}</p>
                `;
            } else {
                analysisElement.innerHTML = '选择一步棋查看分析';
            }
        }
        
        function updateMoveList() {
            const moveItems = document.querySelectorAll('.move-item');
            moveItems.forEach((item, index) => {
                if (index === currentMoveIndex) {
                    item.classList.add('active');
                } else {
                    item.classList.remove('active');
                }
            });
        }
        
        function selectMove(index) {
            currentMoveIndex = index;
            renderBoard();
            updateAnalysis();
            updateMoveList();
        }
        
        function goToStart() {
            selectMove(0);
        }
        
        function goToPrevious() {
            if (currentMoveIndex > 0) {
                selectMove(currentMoveIndex - 1);
            }
        }
        
        function goToNext() {
            if (currentMoveIndex < gameData.moves.length - 1) {
                selectMove(currentMoveIndex + 1);
            }
        }
        
        function goToEnd() {
            selectMove(gameData.moves.length - 1);
        }
        
        // 初始化
        renderBoard();
        updateMoveList();
    </script>
</body>
</html>
        """
        
        template_path = os.path.join(self.templates_dir, "replay_template.html")
        with open(template_path, "w", encoding="utf-8") as f:
            f.write(template_content)
    
    def generate_replay_page(self, pgn_content, analysis_results):
        """生成复盘网页"""
        # 解析PGN生成走棋列表
        moves = []
        # 这里简化处理，实际应用中需要解析PGN内容
        example_moves = [
            {"move_number": 1, "white": "e4", "black": "e5"},
            {"move_number": 2, "white": "Nf3", "black": "Nc6"},
            {"move_number": 3, "white": "Bb5", "black": "a6"},
            {"move_number": 4, "white": "Ba4", "black": "Nf6"},
            {"move_number": 5, "white": "O-O", "black": "Be7"}
        ]
        
        # 加载模板
        template_path = os.path.join(self.templates_dir, "replay_template.html")
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
        
        template = Template(template_content)
        
        # 渲染模板
        html_content = template.render(
            moves=example_moves,
            analysis=analysis_results
        )
        
        # 保存生成的HTML文件
        timestamp = os.path.splitext(os.path.basename(pgn_content))[0] if isinstance(pgn_content, str) and "." in pgn_content else "replay"
        output_file = os.path.join(self.output_dir, f"{timestamp}.html")
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"复盘网页已生成: {output_file}")
        return output_file