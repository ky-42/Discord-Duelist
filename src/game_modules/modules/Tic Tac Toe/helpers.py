from typing import List


def check_win(board: List[List[int]]) -> int:
    """
    Checks board for a winner

    Returns 1 if user 1 won, 2 if user 2 won,
    -1 if tie and 0 if no winner
    """

    # Check rows
    for row in board:
        if row[0] == row[1] == row[2] != 0:
            return row[0]

    # Check columns
    for col in range(3):
        if board[0][col] == board[1][col] == board[2][col] != 0:
            return board[0][col]

    # Check diagonals
    if board[0][0] == board[1][1] == board[2][2] != 0:
        return board[0][0]
    if board[0][2] == board[1][1] == board[2][0] != 0:
        return board[0][2]

    # Check for a tie
    if all(row.count(0) == 0 for row in board):
        return -1

    # No winner
    return 0
