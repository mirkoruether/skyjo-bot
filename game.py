"""
SKYJO game
"""

from calendar import c
import itertools
import random
import typing
import abc
import numpy as np

START_CARD_DECK = list(itertools.chain.from_iterable([
    [-2] * 5,
    [ 0] * 15,
    [-1] * 10,
    [ 1] * 10,
    [ 2] * 10,
    [ 3] * 10,
    [ 4] * 10,
    [ 5] * 10,
    [ 6] * 10,
    [ 7] * 10,
    [ 8] * 10,
    [ 9] * 10,
    [10] * 10,
    [11] * 10,
    [12] * 10,
]))

class IllegalGameAction(RuntimeError):
    pass

class CardStatus:
    HIDDEN = 0
    REVEALED = 1
    GONE = 2

class CurrentGameInfo:
    _values:np.ndarray = None
    _status:np.ndarray = None
    _open:int = None

    def __init__(self, values, status, topdis) -> None:
        self._values = values
        self._status = status
        self._topdis = topdis

class Player(abc.ABC):
    def reveal_two(self, cgi:CurrentGameInfo) -> typing.Tuple[int, int]:
        return random.randint(0, 11), random.randint(0, 11)

    @abc.abstractmethod
    def choose_draw_from_discarded(self, cgi:CurrentGameInfo) -> bool:
        pass

    @abc.abstractmethod
    def choose_action(self, cgi:CurrentGameInfo, card:int) -> typing.Tuple[bool, int]:
        pass

class Game:
    _deck : typing.List[int] = None
    _discarded : typing.List[int] = None
    _topdiscard : int = None
    _player_card_value : np.ndarray = None
    _player_card_status : np.ndarray = None

    _players : typing.List[Player] = None

    def __init__(self, players) -> None:
        self._players = players

    def play_round(self) -> np.ndarray:
        self.init_next_round()
        gameinfo = self.calculate_game_info()

        # Players each reveal two cards
        for i, p in enumerate(self._players):
            j1, j2 = p.reveal_two(gameinfo)
            self._player_card_status[i, j1] = CardStatus.REVEALED
            self._player_card_status[i, j2] = CardStatus.REVEALED

        # Player with the highest revealed sum starts
        gameinfo = self.calculate_game_info()
        playeridx = gameinfo._values.sum(axis=1).argmax()
        turnno = 0
        turncnt = 500
        finishing_playeridx = None

        while turnno <= turncnt:
            gameinfo = self.calculate_game_info()
            player = self._players[playeridx]

            # Choose between drawing a new card or taking the top discarded one
            if player.choose_draw_from_discarded():
                card = self._topdiscard
                self._topdiscard = None
            else:
                card = self.draw()

            # Choose an action
            valid_action = False
            while not valid_action:
                swap, cardidx = player.choose_action(gameinfo, card)
                valid_action = self.validate_action(playeridx, swap, cardidx)

            # Apply action
            if swap:
                old_card = self._player_card_value[playeridx, cardidx]
                self._player_card_value[playeridx, cardidx] = card
                self.discard(old_card)
            else:
                self._player_card_status[playeridx, cardidx] = CardStatus.REVEALED
                self.discard(card)

            # Check if triplet is present
            # If yes, set status to "gone", value to "0" and discard
            self.check_and_handle_triplets(playeridx)

            # Check if the game is finished (and was not finished before)
            # If yes the other players only get one more turn
            if finishing_playeridx is None and self.check_game_finished():
                finishing_playeridx = playeridx
                turncnt = turnno + len(self._players)

            turnno = turnno + 1
            playeridx = (playeridx + 1) % len(self._players)
        # end while 

        # Conclude game
        self._player_card_status = np.where(
            self._player_card_status == CardStatus.HIDDEN,
            CardStatus.REVEALED,
            self._player_card_status,
        )

        for i in range(len(self._players)):
            self.check_and_handle_triplets(i)

        final_values = self._player_card_value.sum(axis=1)
        if finishing_playeridx is not None:
            if final_values[finishing_playeridx] > final_values.min(): # ToDo: It's also x2 if a second player has equal score
                final_values[finishing_playeridx] = 2 * final_values[finishing_playeridx]

        return final_values

    def init_next_round(self):
        self._discarded = []
        self._player_card_value = np.zeros((len(self._players), 12))
        self._player_card_status = np.zeros((len(self._players), 12))

        self._deck = START_CARD_DECK.copy()
        random.shuffle(self._deck)

        for i in range(len(self._players)):
            for j in range(12):
                self._player_card_value[i, j] = self.draw()

        self._topdiscard = self.draw()

        return

    def check_game_finished(self) -> bool:
        return (self._player_card_status != CardStatus.HIDDEN).all(axis=1).any()

    def check_and_handle_triplets(self, playeridx) -> None:
        for i in range(4):
            if (self._player_card_status[playeridx, 3*i:3*(i+1)] == CardStatus.REVEALED).all()\
                and (self._player_card_value[playeridx, 3*i:3*(i+1)] == self._player_card_value[playeridx, 3*i]).all():

                triplet_card = self._player_card_value[playeridx, 3*i]
                self._player_card_status[playeridx, 3*i:3*(i+1)] = CardStatus.GONE
                self._player_card_value[playeridx, 3*i:3*(i+1)] = 0
                for i in range(3):
                    self.discard(triplet_card)

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

    def discard(self, card:int):
        if self._topdiscard is not None:
            self._discarded.append(self._topdiscard)
        self._topdiscard = card

    def validate_action(self, playeridx:int, swap:bool, cardidx:int) -> bool:
        if swap and self._player_card_status[playeridx, cardidx] == CardStatus.GONE:
            return False

        if not swap and self._player_card_status[playeridx, cardidx] != CardStatus.HIDDEN:
            return False

        return True








