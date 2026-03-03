"""
Bot V2 — Engine trung bình.

Thuật toán: Iterative Deepening + Alpha-Beta + Transposition Table
            + Null-Move Pruning + LMR + Killer + History heuristic.
Đánh giá: Material + PST + Bishop pair + Pawn structure + King safety.
"""

import chess
import chess.polyglot
import numpy as np

INF = 999_999

PIECE_VALUES = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   20_000,
}

PST = {
    chess.PAWN: [
         0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
         5,  5, 10, 25, 25, 10,  5,  5,
         0,  0,  0, 20, 20,  0,  0,  0,
         5, -5,-10,  0,  0,-10, -5,  5,
         5, 10, 10,-20,-20, 10, 10,  5,
         0,  0,  0,  0,  0,  0,  0,  0,
    ],
    chess.KNIGHT: [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50,
    ],
}


class BotV2:
    """Engine trung bình: Iterative Deepening, TT, Null-move, LMR."""

    def __init__(self):
        self.tt: dict = {}
        self.history = np.zeros((64, 64), dtype=np.int32)
        self.killers = [[None, None] for _ in range(64)]
        self.nodes = 0

    # ─────────────────────────────────────────
    # Evaluation
    # ─────────────────────────────────────────
    def evaluate(self, board: chess.Board) -> int:
        if board.is_checkmate():
            return -INF

        score = 0

        # Material + PST
        for pt, val in PIECE_VALUES.items():
            score += len(board.pieces(pt, chess.WHITE)) * val
            score -= len(board.pieces(pt, chess.BLACK)) * val

        for sq in board.pieces(chess.KNIGHT, chess.WHITE):
            score += PST[chess.KNIGHT][sq]
        for sq in board.pieces(chess.KNIGHT, chess.BLACK):
            score -= PST[chess.KNIGHT][sq ^ 56]

        for sq in board.pieces(chess.PAWN, chess.WHITE):
            score += PST[chess.PAWN][sq ^ 56]   # flip để White nhìn từ dưới
        for sq in board.pieces(chess.PAWN, chess.BLACK):
            score -= PST[chess.PAWN][sq]

        # Bishop pair
        if len(board.pieces(chess.BISHOP, chess.WHITE)) >= 2:
            score += 35
        if len(board.pieces(chess.BISHOP, chess.BLACK)) >= 2:
            score -= 35

        # Pawn structure
        w_files = [0] * 8
        b_files = [0] * 8
        for sq in board.pieces(chess.PAWN, chess.WHITE):
            w_files[chess.square_file(sq)] += 1
        for sq in board.pieces(chess.PAWN, chess.BLACK):
            b_files[chess.square_file(sq)] += 1

        for f in range(8):
            if w_files[f] > 1:
                score -= 12 * (w_files[f] - 1)   # doubled
            if b_files[f] > 1:
                score += 12 * (b_files[f] - 1)
            isolated_w = (f == 0 or w_files[f-1] == 0) and (f == 7 or w_files[f+1] == 0)
            isolated_b = (f == 0 or b_files[f-1] == 0) and (f == 7 or b_files[f+1] == 0)
            if isolated_w and w_files[f]:
                score -= 15
            if isolated_b and b_files[f]:
                score += 15

        # King safety (pawn shield)
        for color in (chess.WHITE, chess.BLACK):
            sign = 1 if color == chess.WHITE else -1
            king_sq = board.king(color)
            if king_sq is None:
                continue
            kf, kr = chess.square_file(king_sq), chess.square_rank(king_sq)
            direction = 1 if color == chess.WHITE else -1
            shield = 0
            for df in (-1, 0, 1):
                f, r = kf + df, kr + direction
                if 0 <= f <= 7 and 0 <= r <= 7:
                    p = board.piece_at(chess.square(f, r))
                    if p and p.piece_type == chess.PAWN and p.color == color:
                        shield += 8
            score += sign * shield

        return score if board.turn == chess.WHITE else -score

    # ─────────────────────────────────────────
    # Move ordering
    # ─────────────────────────────────────────
    def _order_moves(self, board: chess.Board, depth: int,
                     hash_move: chess.Move | None = None) -> list:
        d_idx = min(depth, 63)

        def score(m: chess.Move) -> int:
            if m == hash_move:
                return 1_000_000
            if board.is_capture(m):
                vic = board.piece_at(m.to_square)
                atk = board.piece_at(m.from_square)
                if vic and atk:
                    return 900_000 + PIECE_VALUES[vic.piece_type] * 10 - PIECE_VALUES[atk.piece_type]
            if m in self.killers[d_idx]:
                return 800_000
            return int(self.history[m.from_square][m.to_square])

        return sorted(board.legal_moves, key=score, reverse=True)

    # ─────────────────────────────────────────
    # Quiescence
    # ─────────────────────────────────────────
    def _quiescence(self, board: chess.Board, alpha: int, beta: int) -> int:
        self.nodes += 1
        stand_pat = self.evaluate(board)
        if stand_pat >= beta:
            return beta
        alpha = max(alpha, stand_pat)

        for move in board.generate_legal_captures():
            board.push(move)
            score = -self._quiescence(board, -beta, -alpha)
            board.pop()
            if score >= beta:
                return beta
            alpha = max(alpha, score)

        return alpha

    # ─────────────────────────────────────────
    # Alpha-Beta (with TT, Null-move, LMR)
    # ─────────────────────────────────────────
    def _alpha_beta(self, board: chess.Board, depth: int,
                    alpha: int, beta: int, can_null: bool = True) -> int:
        key = chess.polyglot.zobrist_hash(board)
        hash_move = None

        if key in self.tt:
            tt_depth, tt_val, tt_move = self.tt[key]
            if tt_depth >= depth:
                return tt_val
            hash_move = tt_move

        if depth <= 0:
            return self._quiescence(board, alpha, beta)

        # Null-move pruning
        if can_null and depth >= 3 and not board.is_check():
            board.push(chess.Move.null())
            null_score = -self._alpha_beta(board, depth - 3, -beta, -beta + 1, False)
            board.pop()
            if null_score >= beta:
                return beta

        moves = self._order_moves(board, depth, hash_move)
        if not moves:
            return -(INF - 64) if board.is_check() else 0

        best_val, best_move = -INF, moves[0]

        for i, move in enumerate(moves):
            board.push(move)
            # LMR
            if i > 4 and depth >= 3 and not board.is_capture(move) and not board.is_check():
                score = -self._alpha_beta(board, depth - 2, -alpha - 1, -alpha)
                if score > alpha:
                    score = -self._alpha_beta(board, depth - 1, -beta, -alpha)
            else:
                score = -self._alpha_beta(board, depth - 1, -beta, -alpha)
            board.pop()

            if score >= beta:
                if not board.is_capture(move):
                    self.killers[min(depth, 63)][1] = self.killers[min(depth, 63)][0]
                    self.killers[min(depth, 63)][0] = move
                    self.history[move.from_square][move.to_square] += depth * depth
                return beta

            if score > best_val:
                best_val, best_move = score, move
                alpha = max(alpha, score)

        self.tt[key] = (depth, best_val, best_move)
        return best_val

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────
    def get_best_move(self, board: chess.Board, depth: int = 3) -> chess.Move | None:
        self.nodes = 0
        best_move = None

        for d in range(1, depth + 1):
            alpha, beta = -INF, INF
            moves = self._order_moves(board, d)
            if not moves:
                break
            current_best = moves[0]
            for move in moves:
                board.push(move)
                score = -self._alpha_beta(board, d - 1, -beta, -alpha)
                board.pop()
                if score > alpha:
                    alpha = score
                    current_best = move
            best_move = current_best

        return best_move
