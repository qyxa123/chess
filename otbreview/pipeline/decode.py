#!/usr/bin/env python3
"""
合法性约束解码模块
功能：从观测到的棋盘状态推断走法（核心算法）
"""

import chess
import json
import cv2
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np


def decode_moves_from_states(
    board_states: List[Dict],
    initial_fen: Optional[str] = None,
    output_dir: Optional[str] = None,
    uncertain_threshold: float = 0.1,
    dist_threshold: float = 2.0
) -> Tuple[List[str], List[Dict]]:
    """
    从棋盘状态序列解码走法（改进版）
    
    使用合法性约束：枚举所有合法走法，选择与观测最匹配的
    
    Args:
        board_states: 棋盘状态列表（来自pieces模块）
        initial_fen: 初始FEN（None表示标准初始局面）
        output_dir: 输出目录（保存debug文件）
        uncertain_threshold: top1与top2距离差距阈值（小于此值则uncertain）
        dist_threshold: 最小距离阈值（超过此值则uncertain）
    
    Returns:
        (moves_san, confidence_list)
        moves_san: SAN格式走法列表
        confidence_list: 每步的置信度信息
    """
    if initial_fen is None:
        board = chess.Board()
    else:
        board = chess.Board(initial_fen)
    
    moves_san = []
    confidence_list = []
    uncertain_moves = []
    
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        occupancy_dir = output_path / "occupancy_maps"
        diff_dir = output_path / "diff_heatmaps"
        occupancy_dir.mkdir(exist_ok=True)
        diff_dir.mkdir(exist_ok=True)
    else:
        output_path = None
        occupancy_dir = None
        diff_dir = None
    
    prev_occupancy = _board_state_to_occupancy(board_states[0])
    
    # 保存第一帧的occupancy map
    if occupancy_dir:
        _save_occupancy_map(prev_occupancy, occupancy_dir / "occupancy_map_0000.png")
    
    for step_idx in range(1, len(board_states)):
        curr_occupancy = _board_state_to_occupancy(board_states[step_idx])
        
        # 计算变化格子（用于加权）
        changed_squares = _compute_changed_squares(prev_occupancy, curr_occupancy)
        
        # 找到最佳匹配的走法
        best_move, best_score, candidates = _find_best_move_weighted(
            board=board,
            prev_occupancy=prev_occupancy,
            curr_occupancy=curr_occupancy,
            changed_squares=changed_squares
        )
        
        if best_move is None:
            moves_san.append("??")
            confidence_list.append({
                'uncertain': True,
                'reason': 'no_matching_move',
                'candidates': []
            })
            continue
        
        # 计算置信度
        uncertain = False
        if len(candidates) > 1:
            score_diff = candidates[1]['score'] - best_score
            if score_diff < uncertain_threshold:
                uncertain = True
        if best_score > dist_threshold:
            uncertain = True
        
        # 执行走法
        board.push(best_move)
        san = board.san(best_move)
        moves_san.append(san)
        
        # 记录uncertain moves
        if uncertain:
            uncertain_moves.append({
                'step': step_idx,
                'move': san,
                'score': float(best_score),
                'candidates': [
                    {
                        'move': board.san(c['move']) if c['move'] != best_move else san,
                        'score': float(c['score'])
                    }
                    for c in candidates[:5]  # top5候选
                ]
            })
        
        confidence_list.append({
            'uncertain': uncertain,
            'score': float(best_score),
            'candidates': [
                {
                    'move': board.san(c['move']) if c['move'] != best_move else san,
                    'score': float(c['score'])
                }
                for c in candidates[:3]  # top3候选
            ]
        })
        
        # 保存debug图
        if occupancy_dir:
            _save_occupancy_map(curr_occupancy, occupancy_dir / f"occupancy_map_{step_idx:04d}.png")
        
        if diff_dir:
            _save_diff_heatmap(prev_occupancy, curr_occupancy, changed_squares,
                             diff_dir / f"diff_heatmap_{step_idx:04d}.png")
        
        prev_occupancy = curr_occupancy
    
    # 保存uncertain moves
    if output_path and uncertain_moves:
        uncertain_path = output_path / "uncertain_moves.json"
        with open(uncertain_path, 'w', encoding='utf-8') as f:
            json.dump(uncertain_moves, f, indent=2, ensure_ascii=False)
        print(f"  记录 {len(uncertain_moves)} 个不确定走法到 {uncertain_path}")
    
    return moves_san, confidence_list


def decode_moves(
    board_states: List[Dict],
    initial_fen: Optional[str] = None,
    output_dir: Optional[str] = None
) -> Tuple[List[str], List[Dict]]:
    """
    从棋盘状态序列解码走法（兼容旧接口）
    """
    return decode_moves_from_states(
        board_states=board_states,
        initial_fen=initial_fen,
        output_dir=output_dir
    )


def _board_state_to_occupancy(state: Dict) -> np.ndarray:
    """
    将board_state转换为8x8占用矩阵
    0=empty, 1=light, 2=dark
    """
    return np.array(state['occupancy'], dtype=np.int32)


def _compute_changed_squares(prev: np.ndarray, curr: np.ndarray) -> np.ndarray:
    """
    计算变化格子（布尔矩阵）
    """
    return (prev != curr).astype(np.float32)


def _find_best_move_weighted(
    board: chess.Board,
    prev_occupancy: np.ndarray,
    curr_occupancy: np.ndarray,
    changed_squares: np.ndarray
) -> Tuple[Optional[chess.Move], float, List[Dict]]:
    """
    找到与观测最匹配的合法走法（加权版本）
    
    对变化格子加权更大
    """
    legal_moves = list(board.legal_moves)
    
    if len(legal_moves) == 0:
        return None, float('inf'), []
    
    candidates = []
    
    for move in legal_moves:
        # 创建临时棋盘
        test_board = board.copy()
        test_board.push(move)
        
        # 计算预期占用状态
        expected_occupancy = _fen_to_occupancy(test_board.fen())
        
        # 计算与观测的距离（加权）
        score = _compute_occupancy_distance_weighted(
            expected_occupancy, curr_occupancy, changed_squares
        )
        
        candidates.append({
            'move': move,
            'score': score
        })
    
    # 按分数排序（越小越好）
    candidates.sort(key=lambda x: x['score'])
    
    best = candidates[0]
    return best['move'], best['score'], candidates


def _fen_to_occupancy(fen: str) -> np.ndarray:
    """
    将FEN转换为8x8占用矩阵
    
    注意：需要将light/dark映射到white/black
    这里假设light=white(1), dark=black(2)
    """
    board = chess.Board(fen)
    occupancy = np.zeros((8, 8), dtype=np.int32)
    
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        row = 7 - (square // 8)  # FEN是从上到下，numpy是从下到上
        col = square % 8
        
        if piece is None:
            occupancy[row, col] = 0
        elif piece.color == chess.WHITE:
            occupancy[row, col] = 1  # light
        else:
            occupancy[row, col] = 2  # dark
    
    return occupancy


def _compute_occupancy_distance_weighted(
    expected: np.ndarray,
    observed: np.ndarray,
    changed_squares: np.ndarray
) -> float:
    """
    计算两个占用矩阵的加权距离
    
    - 不匹配的格子计分
    - 对变化格子加权（权重=2.0）
    - 颜色错误（light vs dark）比空/有错误更严重（权重=1.5）
    """
    diff = (expected != observed).astype(np.float32)
    
    # 基础距离：不匹配的格子数
    base_score = diff.sum()
    
    # 加权：变化格子权重更大
    weighted_score = base_score + (diff * changed_squares).sum() * 1.0
    
    # 颜色错误加权（light vs dark）
    color_error = ((expected == 1) & (observed == 2)) | ((expected == 2) & (observed == 1))
    weighted_score += color_error.sum() * 0.5
    
    return float(weighted_score)


def _save_occupancy_map(occupancy: np.ndarray, output_path: Path):
    """
    保存occupancy map可视化
    """
    # 创建彩色图：empty=灰色, light=白色, dark=黑色
    img = np.zeros((800, 800, 3), dtype=np.uint8)
    cell_size = 100
    
    for row in range(8):
        for col in range(8):
            y1 = row * cell_size
            y2 = (row + 1) * cell_size
            x1 = col * cell_size
            x2 = (col + 1) * cell_size
            
            if occupancy[row, col] == 0:
                color = (128, 128, 128)  # 灰色（empty）
            elif occupancy[row, col] == 1:
                color = (255, 255, 255)  # 白色（light）
            else:
                color = (0, 0, 0)  # 黑色（dark）
            
            img[y1:y2, x1:x2] = color
    
    cv2.imwrite(str(output_path), img)


def _save_diff_heatmap(
    prev: np.ndarray,
    curr: np.ndarray,
    changed_squares: np.ndarray,
    output_path: Path
):
    """
    保存差分热力图
    """
    # 创建热力图：变化越大越红
    img = np.zeros((800, 800, 3), dtype=np.uint8)
    cell_size = 100
    
    for row in range(8):
        for col in range(8):
            y1 = row * cell_size
            y2 = (row + 1) * cell_size
            x1 = col * cell_size
            x2 = (col + 1) * cell_size
            
            if changed_squares[row, col] > 0:
                # 计算变化强度
                if prev[row, col] != curr[row, col]:
                    intensity = 255
                else:
                    intensity = 0
                
                # 红色表示变化
                img[y1:y2, x1:x2] = (0, 0, intensity)
            else:
                # 无变化：显示当前状态（半透明）
                if curr[row, col] == 0:
                    color = (64, 64, 64)
                elif curr[row, col] == 1:
                    color = (200, 200, 200)
                else:
                    color = (20, 20, 20)
                img[y1:y2, x1:x2] = color
    
    cv2.imwrite(str(output_path), img)
