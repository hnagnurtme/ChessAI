"""
Bot V1 — Engine đơn giản nhất.

Thuật toán: Alpha-Beta + Quiescence Search + Killer Moves.
Đánh giá: Material + PST (Pawn, Knight).
"""

import chess
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

# Piece-Square Tables
PAWN_PST = np.array([
     0,  5,  5, -10, -10,  5,  5,  0,
     0, 10, -5,   0,   0, -5, 10,  0,
     0, 10, 10,  20,  20, 10, 10,  0,
     5, 15, 15,  25,  25, 15, 15,  5,
    10, 20, 20,  30,  30, 20, 20, 10,
    20, 30, 30,  40,  40, 30, 30, 20,
    50, 50, 50,  50,  50, 50, 50, 50,
     0,  0,  0,   0,   0,  0,  0,  0,
])

KNIGHT_PST = np.array([
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20,   0,   0,   0,   0, -20, -40,
    -30,   0,  10,  15,  15,  10,   0, -30,
    -30,   5,  15,  20,  20,  15,   5, -30,
    -30,   0,  15,  20,  20,  15,   0, -30,
    -30,   5,  10,  15,  15,  10,   5, -30,
    -40, -20,   0,   5,   5,   0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
])


class BotV1:
    """Engine đơn giản: Alpha-Beta + Quiescence + Killer heuristic."""

    def __init__(self):
        self.nodes = 0
        self.killers = [[None, None] for _ in range(10)]

    # ─────────────────────────────────────────
    # Evaluation
    # ─────────────────────────────────────────
    def evaluate(self, board: chess.Board) -> int:
        if board.is_checkmate():
            return -INF
        if board.is_stalemate():
            return 0

        score = 0
        for sq in chess.SQUARES:
            piece = board.piece_at(sq)
            if not piece:
                continue
            value = PIECE_VALUES[piece.piece_type]
            if piece.piece_type == chess.PAWN:
                idx = sq if piece.color else chess.square_mirror(sq)
                value += int(PAWN_PST[idx])
            elif piece.piece_type == chess.KNIGHT:
                idx = sq if piece.color else chess.square_mirror(sq)
                value += int(KNIGHT_PST[idx])
            score += value if piece.color == chess.WHITE else -value

        return score if board.turn == chess.WHITE else -score

    # ─────────────────────────────────────────
    # Move ordering
    # ─────────────────────────────────────────
    def _order_moves(self, board: chess.Board, depth: int) -> list:
        def score(m: chess.Move) -> int:
            s = 0
            if board.is_capture(m):
                victim = board.piece_at(m.to_square)
                aggressor = board.piece_at(m.from_square)
                if victim and aggressor:
                    s += 10 * PIECE_VALUES[victim.piece_type] - PIECE_VALUES[aggressor.piece_type]
            if m in self.killers[depth]:
                s += 10_000
            return s

        return sorted(board.legal_moves, key=score, reverse=True)

    # ─────────────────────────────────────────
    # Quiescence Search
    # ─────────────────────────────────────────
    def _quiescence(self, board: chess.Board, alpha: int, beta: int) -> int:
        self.nodes += 1
        stand_pat = self.evaluate(board)
        if stand_pat >= beta:
            return beta
        alpha = max(alpha, stand_pat)

        for move in board.legal_moves:
            if not board.is_capture(move):
                continue
            board.push(move)
            score = -self._quiescence(board, -beta, -alpha)
            board.pop()
            if score >= beta:
                return beta
            alpha = max(alpha, score)

        return alpha

    # ─────────────────────────────────────────
    # Alpha-Beta
    # ─────────────────────────────────────────
    def _alpha_beta(self, board: chess.Board, depth: int, alpha: int, beta: int) -> int:
        if depth == 0:
            return self._quiescence(board, alpha, beta)

        best = -INF
        for move in self._order_moves(board, depth):
            board.push(move)
            score = -self._alpha_beta(board, depth - 1, -beta, -alpha)
            board.pop()

            best = max(best, score)
            alpha = max(alpha, score)
            if alpha >= beta:
                if move not in self.killers[depth]:
                    self.killers[depth][1] = self.killers[depth][0]
                    self.killers[depth][0] = move
                break

        return best

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────
    def get_best_move(self, board: chess.Board, depth: int = 3) -> chess.Move | None:
        self.nodes = 0
        best_move, alpha = None, -INF

        for move in self._order_moves(board, depth):
            board.push(move)
            score = -self._alpha_beta(board, depth - 1, -INF, -alpha)
            board.pop()
            if score > alpha:
                alpha = score
                best_move = move

        return best_move
