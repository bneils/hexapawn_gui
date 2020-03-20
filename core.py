from random import randint
from os import listdir, system, name
import pickle
from time import sleep

# Player constants.
B = 0x1
H = 0x2

def reflect(board):
    """Fin the vert reflection of a linear board in a 3x3 box"""
    reflected = []
    for i in range(0, 9, 3):
        reflected.extend((board[i + 2], board[i + 1], board[i]))
    return tuple(reflected)

def reflect_vector(vector):
    """Reflects a vector along the vertical middle"""
    return vector[0] - 2 * (vector[0] % 3) + 2, vector[1] - 2 * (vector[1] % 3) + 2

class Move:
    def __init__(self, board, vectors):
        self.board = board  # Contains game pieces in a linear array.
        self.reflected = reflect(board)
        self.vectors = vectors

    def equals(self, board):
        """Determine if the boards are congruent"""
        return tuple(board) == self.board

    def reflects(self, board):
        """Determine if the boards are congruent through a vertical reflection."""
        return tuple(board) == self.reflected


class Bot:
    def __init__(self):
        self.cur_turn = 1
        self.last_move = (None, None, None)    # turn, move index, vector index

        # Initiate a set of choices that the bot can make, given the arrangement of pawns.
        # Vectors show possible pawn placements (a -> b).
        self.choices = {
            1:[Move((0, H, H, H, 0, 0, B, B, B), [(7, 3), (7, 4), (8, 5)]),
               Move((H, 0, H, 0, H, 0, B, B, B), [(6, 3), (6, 4)])],

            2:[Move((0, 0, H, H, 0, 0, B, 0, B), [(8, 5)]),
               Move((0, 0, H, B, H, 0, B, 0, B), [(3, 0), (6, 4), (8, 4), (8, 5)]),
               Move((0, H, 0, B, 0, H, B, 0, B), [(3, 0), (3, 1)]),
               Move((0, H, 0, H, H, 0, B, 0, B), [(6, 4), (8, 4), (8, 5)]),
               Move((0, 0, H, H, H, B, B, B, 0), [(6, 4), (7, 3)]),
               Move((0, 0, H, H, 0, H, B, B, 0), [(7, 3), (7, 4), (7, 5)]),
               Move((H, 0, 0, B, H, H, 0, B, B), [(7, 5), (8, 4)]),
               Move((0, 0, H, H, B, 0, 0, B, B), [(4, 1), (4, 2), (7, 3), (8, 5)]),
               Move((0, 0, H, 0, H, 0, 0, B, B), [(8, 4), (8, 5)]),
               Move((H, 0, 0, 0, H, 0, 0, B, B), [(8, 4), (8, 5)]),
               Move((H, 0, 0, 0, B, H, 0, B, B), [(4, 0), (4, 1), (7, 5)])],

            3:[Move((0, 0, 0, B, H, 0, 0, 0, B), [(3, 0), (8, 4), (8, 5)]),
               Move((0, 0, 0, B, B, H, 0, 0, B), [(3, 0), (4, 1)]),
               Move((0, 0, 0, B, H, 0, B, 0, 0), [(3, 0), (6, 4)]),
               Move((0, 0, 0, B, B, H, B, 0, 0), [(3, 0), (4, 1)]),
               Move((0, 0, 0, H, H, B, 0, B, 0), [(5, 2), (7, 3)]),
               Move((0, 0, 0, B, H, H, 0, B, 0), [(3, 0), (7, 5)]),
               Move((0, 0, 0, 0, B, H, 0, B, 0), [(4, 1), (7, 5)]),
               Move((0, 0, 0, H, B, 0, 0, B, 0), [(4, 1), (7, 3)]),
               Move((0, 0, 0, H, B, B, 0, 0, B), [(4, 1), (5, 2)]),
               Move((0, 0, 0, 0, H, B, 0, 0, B), [(5, 2), (8, 4)]),
               Move((0, 0, 0, H, H, H, B, 0, 0), [(6, 4)])]
        }

    def play_again(self):
        """Reset the bot's current turn."""
        self.cur_turn = 1

    def make_turn(self, board):
        """Decide which move to use. Returns the killed pawn and
        which move it just made as a vector."""

        if self.cur_turn > 3:
            raise Exception("Bot has taken too many turns.")

        abstract_board = [(p.type if p else 0) for p in board]

        move_num = 0
        for move in self.choices[self.cur_turn]:
            # Randomly choose which piece to move.
            ## Bot may do nothing for moves that only have 1 action
            if not len(move.vectors):
                continue

            # Choose a random vector if the board matches
            if move.equals(abstract_board):
                v = randint(0, len(move.vectors) - 1)
                vector = move.vectors[v]
            elif move.reflects(abstract_board):
                v = randint(0, len(move.vectors) - 1)
                vector = reflect_vector(move.vectors[v])
            else:
                move_num += 1
                continue  # move doesn't match

            # Move the game piece.
            killed_pawn = board[vector[1]]
            board[vector[1]] = board[vector[0]]
            board[vector[0]] = None
            break
        else:
            v = vector = killed_pawn = None

        self.last_move = (self.cur_turn, move_num, v)
        self.cur_turn += 1

        return killed_pawn, vector

    def inform_lost(self):
        """Remove the losing move from the bot's list of options."""
        if None not in self.last_move:
            self.choices[self.last_move[0]][self.last_move[1]].vectors.pop(self.last_move[2])


def win_check(board, last_player):
    """Returns which player won."""

    board = [(p.type if p else 0) for p in board]

    # All pawns are eliminated
    if H not in board:
        return B
    if B not in board:
        return H

    # A pawn is on the other side of the board
    if B in board[:3]:
        return B
    if H in board[-3:]:
        return H

    # If the player can't make valid moves then the bot can't either.
    for i in range(6):
        col = i % 3
        # Check that the human can make moves
        if board[i] == H and (col == 0 and (board[i + 3] == 0 or board[i + 4] == B) or
                              col == 1 and (board[i + 3] == 0 or board[i + 2] == B or board[i + 4] == B) or
                              col == 2 and (board[i + 3] == 0 or board[i + 2] == B)):
            return

    # Both players are blocked.
    return last_player
