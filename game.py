"""
SKYJO game
"""

import itertools
import random

import typing
import numpy as np

START_CARD_DECK = np.array(itertools.chain.from_iterable([
    [-2] * 10,

]))

 
class CardStatus:
    HIDDEN = 0
    REVEALED = 1
    GONE = 2

class CurrentGameInfo:
    _values = None
    _status = None
    _open = None

    def __init__(self, values, status, topdis) -> None:
        self._values = values
        self._status = status
        self._topdis = topdis

class Player:
    def reveal_two(cgi:CurrentGameInfo) -> typing.Tuple[int, int]:
        raise NotImplementedError()

class RoundResult:
    pass

class GameResult:
    pass

class Game:
    _deck = None
    _discarded = None
    _topdiscard = None
    _player_card_value = None
    _player_card_status = None

    _players : typing.List[Player] = None

    def __init__(self, players) -> None:
        self._players = players

    def play_round(self) -> RoundResult:
        self.init_next_round()
        gameinfo = self.calculate_game_info()

        for i, p in enumerate(self._players):
            j1, j2 = p.reveal_two()
            self._player_card_status[i, j1] = CardStatus.REVEALED
            self._player_card_status[i, j2] = CardStatus.REVEALED

        # ...

    def init_next_round(self):
        self._discarded = np.zeros(0)
        self._player_card_value = np.zeros((len(self._players), 12))
        self._player_card_status = np.zeros((len(self._players), 12))

        self._deck = START_CARD_DECK.copy()
        random.shuffle(self._deck)

        for i in range(len(self._players)):
            for j in range(12):
                self._player_card_value[i, j] = self.draw()

        self._topdiscard = self.draw()

        return

    def calculate_game_info(self) -> CurrentGameInfo:
        return CurrentGameInfo(
            values=np.where(self._player_card_status == CardStatus.REVEALED, self._player_card_value, 0),
            status=self._player_card_status,
            topdis=self._topdiscard 
        )

    def draw(self):
        result = self._deck.pop(0)
        if len(self._deck) == 0:
            self._deck = self._discarded
            self._discarded = []
            random.shuffle(self._deck)
        return result







