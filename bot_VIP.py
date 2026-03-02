import chess
import chess.polyglot
import numpy as np
import time

INF = 999999
MATE_SCORE = 900000

# ──────────────────────────────────────────────────────────
# PIECE VALUES (centipawns)
# ──────────────────────────────────────────────────────────
PIECE_VALUES = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   20000,
}

# ──────────────────────────────────────────────────────────
# PIECE-SQUARE TABLES (white perspective, index = square a1..h8)
# Flip vertically for black.
# ──────────────────────────────────────────────────────────
PST_PAWN = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]

PST_KNIGHT = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
]

PST_BISHOP = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
]

PST_ROOK = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
]

PST_QUEEN = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20,
]

PST_KING_MG = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20,
]

PST_KING_EG = [
    -50,-40,-30,-20,-20,-30,-40,-50,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50,
]

PST = {
    chess.PAWN:   PST_PAWN,
    chess.KNIGHT: PST_KNIGHT,
    chess.BISHOP: PST_BISHOP,
    chess.ROOK:   PST_ROOK,
    chess.QUEEN:  PST_QUEEN,
    chess.KING:   PST_KING_MG,  # will blend with EG below
}

def pst_score(piece_type, square, color, endgame_factor=0.0):
    """Return piece-square bonus for a piece, always from white perspective."""
    # Mirror square vertically for black
    idx = square if color == chess.WHITE else chess.square_mirror(square)

    if piece_type == chess.KING:
        mg = PST_KING_MG[idx]
        eg = PST_KING_EG[idx]
        return int(mg * (1 - endgame_factor) + eg * endgame_factor)

    return PST[piece_type][idx]


# ──────────────────────────────────────────────────────────
# TRANSPOSITION TABLE ENTRY FLAGS
# ──────────────────────────────────────────────────────────
TT_EXACT = 0
TT_LOWER = 1   # fail-high (lower bound)
TT_UPPER = 2   # fail-low  (upper bound)


# ──────────────────────────────────────────────────────────
# MAIN BOT CLASS
# ──────────────────────────────────────────────────────────
class NNBt:
    def __init__(self, model_path=None):
        self.tt: dict = {}          # Transposition Table
        self.history = np.zeros((64, 64), dtype=np.int32)
        self.killers = [[None, None] for _ in range(64)]
        self.nodes = 0
        self.start_time = 0.0
        self.time_limit = 5.0       # seconds per move (used in iterative deepening)

    # ─────────────────────────────────────────
    # ENDGAME FACTOR  (0 = opening, 1 = endgame)
    # ─────────────────────────────────────────
    def _endgame_factor(self, board: chess.Board) -> float:
        material = sum(
            PIECE_VALUES[p.piece_type]
            for p in board.piece_map().values()
            if p.piece_type != chess.KING
        )
        # Full material ~ 7800 (both sides); pure king vs king = 0
        return max(0.0, 1.0 - material / 7800.0)

    # ─────────────────────────────────────────
    # PAWN STRUCTURE EVALUATION
    # ─────────────────────────────────────────
    def _pawn_structure(self, board: chess.Board) -> int:
        score = 0
        for color in (chess.WHITE, chess.BLACK):
            sign = 1 if color == chess.WHITE else -1
            pawns = board.pieces(chess.PAWN, color)
            files_with_pawns = [chess.square_file(sq) for sq in pawns]

            # Doubled pawns penalty
            for f in range(8):
                cnt = files_with_pawns.count(f)
                if cnt > 1:
                    score -= sign * 20 * (cnt - 1)

            # Isolated pawn penalty
            for f in range(8):
                if f not in files_with_pawns:
                    continue
                neighbours = [f - 1, f + 1]
                if all(n not in files_with_pawns for n in neighbours if 0 <= n <= 7):
                    score -= sign * 15

            # Passed pawn bonus
            opp_pawns = board.pieces(chess.PAWN, not color)
            opp_files = [chess.square_file(sq) for sq in opp_pawns]
            for sq in pawns:
                f = chess.square_file(sq)
                r = chess.square_rank(sq)
                adj = [f - 1, f, f + 1]
                blocking = [
                    osq for osq in opp_pawns
                    if chess.square_file(osq) in adj
                    and (
                        (color == chess.WHITE and chess.square_rank(osq) > r) or
                        (color == chess.BLACK and chess.square_rank(osq) < r)
                    )
                ]
                if not blocking:
                    # Bonus scales with advancement
                    advance = r if color == chess.WHITE else 7 - r
                    score += sign * (10 + advance * 8)

        return score

    # ─────────────────────────────────────────
    # KING SAFETY EVALUATION
    # ─────────────────────────────────────────
    def _king_safety(self, board: chess.Board, endgame_factor: float) -> int:
        if endgame_factor > 0.6:
            return 0   # King safety less relevant in endgame

        score = 0
        for color in (chess.WHITE, chess.BLACK):
            sign = 1 if color == chess.WHITE else -1
            king_sq = board.king(color)
            if king_sq is None:
                continue

            # Pawn shield: pawns in front of king
            shield_squares = []
            direction = 1 if color == chess.WHITE else -1
            kf = chess.square_file(king_sq)
            kr = chess.square_rank(king_sq)
            for df in [-1, 0, 1]:
                sf = kf + df
                sr = kr + direction
                if 0 <= sf <= 7 and 0 <= sr <= 7:
                    shield_sq = chess.square(sf, sr)
                    if board.piece_at(shield_sq) == chess.Piece(chess.PAWN, color):
                        score += sign * 10
                    else:
                        score -= sign * 8  # missing pawn shield

            # Penalty for open files near king
            for df in [-1, 0, 1]:
                f = kf + df
                if not (0 <= f <= 7):
                    continue
                file_mask = chess.BB_FILES[f]
                if not (board.pieces(chess.PAWN, chess.WHITE) & file_mask) and \
                   not (board.pieces(chess.PAWN, chess.BLACK) & file_mask):
                    score -= sign * 15   # fully open file near king

            # Penalty proportional to attacker count near king
            king_zone = board.attacks(king_sq)
            attackers = 0
            for sq in king_zone:
                for pt in [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]:
                    if board.pieces(pt, not color) & chess.BB_SQUARES[sq]:
                        attackers += 1
            score -= sign * attackers * 12

        return score

    # ─────────────────────────────────────────
    # CENTER CONTROL
    # ─────────────────────────────────────────
    def _center_control(self, board: chess.Board) -> int:
        CENTER = [chess.D4, chess.E4, chess.D5, chess.E5]
        EXT_CENTER = [chess.C3, chess.D3, chess.E3, chess.F3,
                      chess.C4,                   chess.F4,
                      chess.C5,                   chess.F5,
                      chess.C6, chess.D6, chess.E6, chess.F6]
        score = 0
        for sq in CENTER:
            w_att = len(board.attackers(chess.WHITE, sq))
            b_att = len(board.attackers(chess.BLACK, sq))
            score += (w_att - b_att) * 5
        for sq in EXT_CENTER:
            w_att = len(board.attackers(chess.WHITE, sq))
            b_att = len(board.attackers(chess.BLACK, sq))
            score += (w_att - b_att) * 2
        return score

    # ─────────────────────────────────────────
    # MAIN EVALUATION (always returns score for side to move)
    # ─────────────────────────────────────────
    def evaluate(self, board: chess.Board) -> int:
        if board.is_checkmate():
            return -MATE_SCORE
        if board.is_stalemate() or board.is_insufficient_material():
            return 0

        eg = self._endgame_factor(board)
        score = 0
        white_bishops = 0
        black_bishops = 0

        for square, piece in board.piece_map().items():
            value = PIECE_VALUES[piece.piece_type]
            pst   = pst_score(piece.piece_type, square, piece.color, eg)

            if piece.piece_type == chess.BISHOP:
                if piece.color == chess.WHITE:
                    white_bishops += 1
                else:
                    black_bishops += 1

            if piece.color == chess.WHITE:
                score += value + pst
            else:
                score -= value + pst

        # Bishop pair bonus
        if white_bishops >= 2: score += 30
        if black_bishops >= 2: score -= 30

        # Mobility
        mobility = len(list(board.legal_moves))
        score += (2 * mobility) if board.turn == chess.WHITE else (-2 * mobility)

        # Structural / positional bonuses
        score += self._pawn_structure(board)
        score += self._king_safety(board, eg)
        score += self._center_control(board)

        return score if board.turn == chess.WHITE else -score

    # ─────────────────────────────────────────
    # MOVE ORDERING
    # ─────────────────────────────────────────
    def order_moves(self, board: chess.Board, depth: int, tt_move=None):
        moves = list(board.legal_moves)

        def score_move(move):
            s = 0
            # TT / hash move gets highest priority
            if move == tt_move:
                return 2_000_000

            if board.is_capture(move):
                victim   = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                if victim and attacker:
                    s += 1_000_000 + 10 * PIECE_VALUES[victim.piece_type] - PIECE_VALUES[attacker.piece_type]
                else:
                    s += 1_000_000

            # Promotion
            if move.promotion:
                s += 800_000 + PIECE_VALUES.get(move.promotion, 0)

            # Killer moves
            kid = min(depth, len(self.killers) - 1)
            if move in self.killers[kid]:
                s += 900_000

            # History
            s += int(self.history[move.from_square][move.to_square])

            return s

        moves.sort(key=score_move, reverse=True)
        return moves

    # ─────────────────────────────────────────
    # QUIESCENCE SEARCH
    # ─────────────────────────────────────────
    def quiescence(self, board: chess.Board, alpha: int, beta: int, ply: int = 0) -> int:
        self.nodes += 1

        stand_pat = self.evaluate(board)

        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        # Delta pruning: if even capturing the best piece can't improve alpha, skip
        DELTA = 900  # queen value
        if stand_pat + DELTA < alpha:
            return alpha

        for move in board.legal_moves:
            if not board.is_capture(move) and not move.promotion:
                continue

            board.push(move)
            score = -self.quiescence(board, -beta, -alpha, ply + 1)
            board.pop()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

    # ─────────────────────────────────────────
    # ALPHA-BETA (Negamax + TT + NMP + FP + LMR)
    # ─────────────────────────────────────────
    def alpha_beta(
        self,
        board: chess.Board,
        depth: int,
        alpha: int,
        beta: int,
        ply: int = 0,
        null_allowed: bool = True,
    ) -> int:
        self.nodes += 1

        # Time check every 4096 nodes
        if self.nodes & 4095 == 0:
            if time.time() - self.start_time > self.time_limit:
                return self.evaluate(board)

        # ── Transposition Table lookup ──
        key = chess.polyglot.zobrist_hash(board)
        tt_move = None
        if key in self.tt:
            tt_depth, tt_score, tt_flag, tt_mv = self.tt[key]
            tt_move = tt_mv
            if tt_depth >= depth:
                if tt_flag == TT_EXACT:
                    return tt_score
                elif tt_flag == TT_LOWER:
                    alpha = max(alpha, tt_score)
                elif tt_flag == TT_UPPER:
                    beta  = min(beta,  tt_score)
                if alpha >= beta:
                    return tt_score

        # ── Terminal / leaf ──
        if depth <= 0:
            return self.quiescence(board, alpha, beta)

        if board.is_checkmate():
            return -(MATE_SCORE - ply)
        if board.is_stalemate() or board.is_insufficient_material():
            return 0

        in_check = board.is_check()
        # Check extension
        if in_check:
            depth += 1

        # ── Null Move Pruning ──
        NULL_REDUCTION = 3
        if (
            null_allowed
            and not in_check
            and depth >= NULL_REDUCTION + 1
            and self._endgame_factor(board) < 0.8   # avoid NMP in endgame
        ):
            board.push(chess.Move.null())
            null_score = -self.alpha_beta(board, depth - 1 - NULL_REDUCTION, -beta, -beta + 1, ply + 1, null_allowed=False)
            board.pop()
            if null_score >= beta:
                return beta   # fail-hard cutoff

        # ── Razoring ──
        RAZOR_MARGIN = 300
        if depth == 1 and not in_check:
            if self.evaluate(board) + RAZOR_MARGIN < alpha:
                return self.quiescence(board, alpha, beta)

        # ── Move loop ──
        moves = self.order_moves(board, ply, tt_move)

        if not moves:
            return -(MATE_SCORE - ply) if in_check else 0

        best_score = -INF
        best_move  = None
        orig_alpha = alpha
        move_count = 0

        # Futility margin by depth
        FUTILITY_MARGINS = {1: 100, 2: 300, 3: 500}

        for move in moves:
            is_capture   = board.is_capture(move)
            gives_check  = board.gives_check(move)
            is_promotion = bool(move.promotion)

            # ── Futility Pruning ──
            if (
                depth in FUTILITY_MARGINS
                and not in_check
                and not is_capture
                and not gives_check
                and not is_promotion
                and move_count > 0
            ):
                futility_score = self.evaluate(board) + FUTILITY_MARGINS[depth]
                if futility_score <= alpha:
                    move_count += 1
                    continue

            board.push(move)

            # ── Late Move Reduction ──
            if (
                move_count >= 3
                and depth >= 3
                and not is_capture
                and not in_check
                and not gives_check
                and not is_promotion
            ):
                # Reduced search
                reduction = 1 if move_count < 6 else 2
                score = -self.alpha_beta(board, depth - 1 - reduction, -alpha - 1, -alpha, ply + 1)
                # Re-search if promising
                if score > alpha:
                    score = -self.alpha_beta(board, depth - 1, -beta, -alpha, ply + 1)
            else:
                score = -self.alpha_beta(board, depth - 1, -beta, -alpha, ply + 1)

            board.pop()
            move_count += 1

            if score > best_score:
                best_score = score
                best_move  = move

            if score > alpha:
                alpha = score

            if alpha >= beta:
                # Killer move update
                if not is_capture:
                    kid = min(ply, len(self.killers) - 1)
                    if move not in self.killers[kid]:
                        self.killers[kid][1] = self.killers[kid][0]
                        self.killers[kid][0] = move
                    # History update
                    self.history[move.from_square][move.to_square] += depth * depth
                break

        # ── Store in TT ──
        if best_score <= orig_alpha:
            tt_flag = TT_UPPER
        elif best_score >= beta:
            tt_flag = TT_LOWER
        else:
            tt_flag = TT_EXACT
        self.tt[key] = (depth, best_score, tt_flag, best_move)

        return best_score

    # ─────────────────────────────────────────
    # ITERATIVE DEEPENING
    # ─────────────────────────────────────────
    def get_best_move(self, board: chess.Board, depth: int = 5, time_limit: float = 5.0) -> chess.Move:
        self.time_limit  = time_limit
        self.start_time  = time.time()
        self.nodes       = 0
        self.killers     = [[None, None] for _ in range(64)]
        # Do NOT reset history between moves — it accumulates strategic knowledge

        best_move  = None
        best_score = -INF

        for current_depth in range(1, depth + 1):
            if time.time() - self.start_time > self.time_limit:
                break

            alpha  = -INF
            beta   = INF

            # Aspiration windows (only from depth >= 4)
            if current_depth >= 4 and best_score not in (-INF, INF):
                WINDOW = 50
                alpha = best_score - WINDOW
                beta  = best_score + WINDOW

            iteration_best_move  = best_move
            iteration_best_score = -INF

            moves = self.order_moves(board, current_depth,
                                     tt_move=self.tt.get(chess.polyglot.zobrist_hash(board), (None,) * 4)[3])

            for move in moves:
                if time.time() - self.start_time > self.time_limit:
                    break

                board.push(move)
                score = -self.alpha_beta(board, current_depth - 1, -beta, -alpha, ply=1)
                board.pop()

                if score > iteration_best_score:
                    iteration_best_score = score
                    iteration_best_move  = move

                if score > alpha:
                    alpha = score

                # Aspiration window failure: full re-search
                if alpha >= beta:
                    if current_depth >= 4:
                        # Widen window and redo
                        alpha = -INF
                        beta  = INF
                        board.push(move)
                        score = -self.alpha_beta(board, current_depth - 1, -beta, -alpha, ply=1)
                        board.pop()
                        if score > iteration_best_score:
                            iteration_best_score = score
                            iteration_best_move  = move
                        if score > alpha:
                            alpha = score
                    break

            # Only update global best if iteration completed without timeout
            if iteration_best_move:
                best_move  = iteration_best_move
                best_score = iteration_best_score

        return best_move
