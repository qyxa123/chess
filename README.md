# OTBReview - 实体棋盘视频分析系统

将实体棋盘视频转换为PGN，并使用Stockfish进行复盘分析。

## 功能特性

- 📹 **视频解析**：自动从视频中抽取稳定局面帧
- 🎯 **棋盘定位**：支持ArUco/AprilTag标记或纯视觉检测
- ♟️ **走法识别**：基于合法性约束的解码算法
- 🧠 **Stockfish分析**：本地离线分析，无需会员
- 📊 **可视化复盘**：仿chess.com风格的网页复盘界面
- 🔧 **纠错机制**：低置信度走法可手动修正
- 🏷️ **棋子贴码识别**：支持1-32号棋子贴纸，逐帧还原piece_id网格并解码走法

## 快速开始

### 网页界面（小白推荐）

最简单的使用方式，无需记忆命令行。

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **启动网页**
   ```bash
   python scripts/start_web.py
   ```
   或者
   ```bash
   streamlit run app.py
   ```

3. **使用流程**
   - 浏览器会自动打开 http://localhost:8501
   - 点击 "Browse files" 上传视频
   - 点击 "🚀 Run Analysis"
   - 等待运行完成，直接查看 PGN 和调试图片

### 棋子贴码识别版（Tag 模式）

该模式假设棋盘四角贴有ArUco 0/1/2/3用于warp对齐，棋子顶部贴1-32号小tag用于定位身份。

流程概览：

1. **稳定帧抽取**：沿用现有`extract_stable_frames`，保持fps与阈值逻辑不变。
2. **棋盘warp**：在每个稳定帧上检测0-3号ArUco四角，warp到800x800。
3. **标签检测**：在warp图上检测1-32号标签，过滤太小的框并输出中心坐标与ID；同一格子/同一ID冲突时取面积更大的检测。
4. **落格映射**：按 `col=floor(x/(size/8)), row=floor(y/(size/8))` 生成8x8的piece_id矩阵，保存为`debug/board_ids.json`。
5. **可视化**：在`debug/tag_overlays/`输出每帧`overlay_xxxx.png`，`debug/tag_overlay.png`为第一帧示例，同时保存8x8矩阵。
6. **走法解码**：利用`config/piece_id_map.json`中的ID→棋子映射，用python-chess比对相邻两帧的piece_id变化，自动推断走法（含吃子、易位、升变）。
7. **输出**：生成`game.pgn`，`analysis.json`以及带「Tag Overlay Viewer」的网页复盘（`index.html`）。

默认ID映射（可在`config/piece_id_map.json`里修改）：

- 1-8：白方a2-h2兵；9-10：白车（a1/h1）；11-12：白马（b1/g1）；13-14：白象（c1/f1）；15：后；16：王。
- 17-24：黑方a7-h7兵；25-26：黑车（a8/h8）；27-28：黑马（b8/g8）；29-30：黑象（c8/f8）；31：后；32：王。

网页复盘新增「Tag Overlay Viewer」页签：可选择帧查看`overlay`叠加图和8x8 piece_id表格，并在侧边展示ID映射，方便核对检测结果。

### 前置要求

- macOS (推荐)
- Python 3.8+
- Stockfish (通过brew安装)
- ffmpeg (用于视频处理)

### 安装步骤

1. **安装系统依赖**
```bash
brew install stockfish ffmpeg
```

2. **克隆仓库**
```bash
git clone https://github.com/qyxa123/chess.git
cd chess
```

3. **创建虚拟环境**
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
```

4. **安装Python依赖**
```bash
pip install -r requirements.txt
```

### Print Piece Tags

- 默认标签尺寸为 **5mm x 5mm**（推荐）。如果棋子顶部空间有限可选 **3mm**，但检测容错会更小。
- 将标签贴在棋子顶部，尽量保持水平，避免强烈反光；贴好后检查标签边界不要被弯折或遮挡。
- 生成打印文件：
```bash
python scripts/generate_piece_tags.py --family apriltag --tag-size-mm 5
```
