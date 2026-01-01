#!/usr/bin/env python3
"""
从warped棋盘帧到PGN的解码脚本
"""

import argparse
import sys
from pathlib import Path
import cv2
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from otbreview.pipeline.pieces import detect_pieces_auto_calibrate
from otbreview.pipeline.decode import decode_moves_from_states
from otbreview.pipeline.pgn import generate_pgn


def main():
    parser = argparse.ArgumentParser(
        description="从warped棋盘帧解码生成PGN"
    )
    parser.add_argument(
        '--warped_dir',
        type=str,
        required=True,
        help='warped棋盘目录（包含warp_*.png）'
    )
    parser.add_argument(
        '--outdir',
        type=str,
        required=True,
        help='输出目录'
    )
    parser.add_argument(
        '--uncertain_threshold',
        type=float,
        default=0.1,
        help='不确定阈值（top1与top2距离差距，默认0.1）'
    )
    parser.add_argument(
        '--dist_threshold',
        type=float,
        default=2.0,
        help='距离阈值（超过此值则不确定，默认2.0）'
    )
    
    args = parser.parse_args()
    
    warped_dir = Path(args.warped_dir)
    if not warped_dir.exists():
        print(f"错误: warped目录不存在: {warped_dir}")
        sys.exit(1)
    
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    debug_dir = outdir / "debug"
    debug_dir.mkdir(exist_ok=True)
    
    # 查找所有warped图像
    warped_files = sorted(warped_dir.glob("warp_*.png"))
    if len(warped_files) == 0:
        print(f"错误: 未找到warped图像文件: {warped_dir}")
        sys.exit(1)
    
    print(f"找到 {len(warped_files)} 张warped图像")
    
    # 步骤1: 识别每帧的棋盘状态
    print("\n=== 步骤1: 识别棋盘状态 ===")
    board_states = []
    calibration_data = None
    
    for i, warped_file in enumerate(warped_files):
        print(f"处理帧 {i+1}/{len(warped_files)}: {warped_file.name}")
        
        warped = cv2.imread(str(warped_file))
        if warped is None:
            print(f"  警告: 无法读取 {warped_file}")
            continue
        
        board_state, calibration_data = detect_pieces_auto_calibrate(
            warped_board=warped,
            frame_idx=i,
            output_dir=str(debug_dir),
            calibration_data=calibration_data
        )
        
        board_states.append(board_state)
    
    # 保存board_states.json
    board_states_path = outdir / "board_states.json"
    with open(board_states_path, 'w', encoding='utf-8') as f:
        json.dump(board_states, f, indent=2, ensure_ascii=False)
    print(f"\n棋盘状态已保存: {board_states_path}")
    
    # 步骤2: 规则推断走法
    print("\n=== 步骤2: 规则推断走法 ===")
    moves_san, confidence_list = decode_moves_from_states(
        board_states=board_states,
        initial_fen=None,  # 标准开局
        output_dir=str(debug_dir),
        uncertain_threshold=args.uncertain_threshold,
        dist_threshold=args.dist_threshold
    )
    
    print(f"推断出 {len(moves_san)} 步走法")
    uncertain_count = sum(1 for c in confidence_list if c.get('uncertain', False))
    if uncertain_count > 0:
        print(f"警告: {uncertain_count} 步置信度较低，请查看 debug/uncertain_moves.json")
    
    # 步骤3: 生成PGN
    print("\n=== 步骤3: 生成PGN ===")
    pgn_content = generate_pgn(moves=moves_san)
    pgn_path = outdir / "game.pgn"
    with open(pgn_path, 'w', encoding='utf-8') as f:
        f.write(pgn_content)
    print(f"PGN已保存: {pgn_path}")
    
    # 保存置信度信息
    confidence_path = outdir / "confidence.json"
    with open(confidence_path, 'w', encoding='utf-8') as f:
        json.dump(confidence_list, f, indent=2, ensure_ascii=False)
    
    print("\n=== 完成 ===")
    print(f"输出目录: {outdir}")
    print(f"\n验收文件:")
    print(f"  - {board_states_path} (棋盘状态)")
    print(f"  - {pgn_path} (PGN文件)")
    print(f"  - {debug_dir / 'occupancy_maps/'} (占用图)")
    print(f"  - {debug_dir / 'diff_heatmaps/'} (差分热力图)")
    print(f"  - {debug_dir / 'uncertain_moves.json'} (不确定走法)")
    print(f"\n验证: 打开 {pgn_path} 在网页回放中查看")


if __name__ == '__main__':
    main()

