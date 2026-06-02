import pytest

from stockrock.engine.board import Board, detect_board, limit_up_ratio


@pytest.mark.parametrize(
    "code,name,board,ratio",
    [
        ("600519", None, Board.MAIN, 0.098),
        ("000001", None, Board.MAIN, 0.098),
        ("300750", None, Board.CHINEXT, 0.198),
        ("688981", None, Board.STAR, 0.198),
        ("830799", None, Board.BSE, 0.298),
        ("000000", "ST海马", Board.ST, 0.048),
    ],
)
def test_limit_up_ratio(code, name, board, ratio):
    assert detect_board(code, name=name) == board
    assert limit_up_ratio(code, name=name) == ratio
