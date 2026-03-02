import chess
import chess.polyglot
import numpy as np

INF = 999999

# Giá trị quân cờ
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

# PST tối giản cho Mã và Tốt để bot có định hướng
PST = {
    chess.PAWN: [
        0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
        5,  5, 10, 25, 25, 10,  5,  5,
        0,  0,  0, 20, 20,  0,  0,  0,
        5, -5,-10,  0,  0,-10, -5,  5,
        5, 10, 10,-20,-20, 10, 10,  5,
        0,  0,  0,  0,  0,  0,  0,  0
    ],
    chess.KNIGHT: [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50
    ]
}

class NNBt:
    def __init__(self, model_path=None):
        self.tt = {}
        self.history = np.zeros((64, 64), dtype=int)
        self.killers = [[None, None] for _ in range(64)]

    def evaluate(self, board):
        if board.is_checkmate(): return -INF
        
        score = 0
        # Tính điểm dựa trên số lượng quân (Rất nhanh)
        for pt, val in PIECE_VALUES.items():
            score += len(board.pieces(pt, chess.WHITE)) * val
            score -= len(board.pieces(pt, chess.BLACK)) * val
        
        # Chỉ cộng PST cho Mã để bot không đi quẩn (Tốt tính sau nếu cần)
        for sq in board.pieces(chess.KNIGHT, chess.WHITE): score += PST[chess.KNIGHT][sq]
        for sq in board.pieces(chess.KNIGHT, chess.BLACK): score -= PST[chess.KNIGHT][sq ^ 56]

        return score if board.turn == chess.WHITE else -score

    def order_moves(self, board, depth, hash_move=None):
        moves = list(board.legal_moves)
        d_idx = min(depth, 63)
        
        def score_move(move):
            if move == hash_move: return 1000000
            if board.is_capture(move):
                vic = board.piece_at(move.to_square)
                atker = board.piece_at(move.from_square)
                if vic and atker:
                    return 900000 + (PIECE_VALUES[vic.piece_type] * 10 - PIECE_VALUES[atker.piece_type])
            if move in self.killers[d_idx]: return 800000
            return self.history[move.from_square][move.to_square]

        moves.sort(key=score_move, reverse=True)
        return moves

    def quiescence(self, board, alpha, beta):
        stand_pat = self.evaluate(board)
        if stand_pat >= beta: return beta
        if alpha < stand_pat: alpha = stand_pat

        for move in board.generate_legal_captures():
            board.push(move)
            score = -self.quiescence(board, -beta, -alpha)
            board.pop()
            if score >= beta: return beta
            if score > alpha: alpha = score
        return alpha

    def alpha_beta(self, board, depth, alpha, beta, can_null=True):
        key = chess.polyglot.zobrist_hash(board)
        hash_move = None
        
        if key in self.tt:
            d, val, m = self.tt[key]
            if d >= depth: return val
            hash_move = m

        if depth <= 0:
            return self.quiescence(board, alpha, beta)

        # --- Null Move Pruning ---
        if can_null and depth >= 3 and not board.is_check():
            board.push(chess.Move.null())
            score = -self.alpha_beta(board, depth - 3, -beta, -beta + 1, False)
            board.pop()
            if score >= beta: return beta

        moves = self.order_moves(board, depth, hash_move)
        if not moves:
            return -INF + 64 if board.is_check() else 0

        best_val = -INF
        best_move = moves[0]

        for i, move in enumerate(moves):
            board.push(move)
            
            # Late Move Reduction (LMR) - Cực mạnh để tăng tốc
            if i > 4 and depth >= 3 and not board.is_capture(move) and not board.is_check():
                score = -self.alpha_beta(board, depth - 2, -alpha - 1, -alpha)
                if score > alpha:
                    score = -self.alpha_beta(board, depth - 1, -beta, -alpha)
            else:
                score = -self.alpha_beta(board, depth - 1, -beta, -alpha)
            
            board.pop()

            if score >= beta:
                if not board.is_capture(move):
                    self.killers[depth][1] = self.killers[depth][0]
                    self.killers[depth][0] = move
                    self.history[move.from_square][move.to_square] += depth * depth
                return beta
            
            if score > best_val:
                best_val = score
                best_move = move
                if score > alpha: alpha = score

        self.tt[key] = (depth, best_val, best_move)
        return best_val

    def get_best_move(self, board, depth=3):
        best_move = None
        # --- Iterative Deepening ---
        # Tìm từ depth 1 lên đến depth mục tiêu
        for d in range(1, depth + 1):
            alpha, beta = -INF, INF
            moves = self.order_moves(board, d)
            if not moves: break
            
            current_best = moves[0]
            for move in moves:
                board.push(move)
                score = -self.alpha_beta(board, d - 1, -beta, -alpha)
                board.pop()
                if score > alpha:
                    alpha = score
                    current_best = move
            best_move = current_best
            
        return best_move