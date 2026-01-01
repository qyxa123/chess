#!/usr/bin/env python3
"""
电脑端/复盘端主程序
功能：视频解析 → PGN → Stockfish → 网页复盘
"""

import os
import sys
from video_parser import VideoParser
from stockfish_analyzer import StockfishAnalyzer
from web_replayer import WebReplayer

class ComputerAnalysisApp:
    def __init__(self):
        self.video_parser = VideoParser()
        self.stockfish_analyzer = StockfishAnalyzer()
        self.web_replayer = WebReplayer()
    
    def process_video(self, video_path):
        """处理视频文件，完成整个流程"""
        if not os.path.exists(video_path):
            print(f"错误：视频文件不存在: {video_path}")
            return False
        
        print("=== 开始处理视频 ===")
        
        # 1. 视频解析 → PGN
        print("\n1. 正在解析视频...")
        pgn_content = self.video_parser.parse_video(video_path)
        
        if not pgn_content:
            print("视频解析失败")
            return False
        
        # 保存PGN文件
        pgn_filename = os.path.splitext(os.path.basename(video_path))[0] + ".pgn"
        with open(pgn_filename, "w", encoding="utf-8") as f:
            f.write(pgn_content)
        print(f"PGN文件已保存: {pgn_filename}")
        
        # 2. Stockfish分析
        print("\n2. 正在分析棋局...")
        analysis_results = self.stockfish_analyzer.analyze_pgn(pgn_content)
        
        if not analysis_results:
            print("棋局分析失败")
            return False
        
        # 保存分析报告
        report_filename = os.path.splitext(os.path.basename(video_path))[0] + "_analysis.md"
        report_content = self.stockfish_analyzer.generate_analysis_report(analysis_results)
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"分析报告已保存: {report_filename}")
        
        # 3. 生成网页复盘
        print("\n3. 正在生成网页复盘...")
        replay_page = self.web_replayer.generate_replay_page(video_path, analysis_results)
        
        print("\n=== 处理完成 ===")
        print(f"视频文件: {video_path}")
        print(f"PGN文件: {pgn_filename}")
        print(f"分析报告: {report_filename}")
        print(f"网页复盘: {replay_page}")
        
        return True
    
    def run(self):
        """运行主程序"""
        if len(sys.argv) < 2:
            print("使用方法: python computer_analysis.py <视频文件路径>")
            return
        
        video_path = sys.argv[1]
        self.process_video(video_path)

if __name__ == "__main__":
    app = ComputerAnalysisApp()
    app.run()