"""
SKYJO game
"""

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

class IllegalActionError(RuntimeError):
    pass

class CardStatus:
    HIDDEN = 0
    REVEALED = 1
    GONE = 2

class CurrentGameInfo:
    _playercnt:int = None
    _values:np.ndarray = None
    _status:np.ndarray = None
    _topdis:int = None
    _turnno:int = None
    _finishing:bool = None

    def __init__(self, playercnt, values, status, topdis, turnno, finishing) -> None:
        self._playercnt = playercnt
        self._values = values
        self._status = status
        self._topdis = topdis
        self._turnno = turnno
        self._finishing = finishing

class GameCore(abc.ABC):
    _player_count : int = None

    _deck : typing.List[int] = None
    _discarded : typing.List[int] = None
    _topdiscard : int = None
    _player_card_value : np.ndarray = None
    _player_card_status : np.ndarray = None

    _active_card : int = None
    _active_playeridx : int = None
    _finishing_playeridx = None

    _turnno : int = None
    _turncnt : int = None

    _roundno : int = 0
    _round_results : np.ndarray = None

    def __init__(self, player_count) -> None:
        self._player_count = player_count

    @abc.abstractmethod
    def action(self) -> int:
        # 0 = Draw card
        # 1 = Take card
        # 2-13 =  Swap card with (X-2)
        # 14-25 = Discard card, reveal (X-14)
        pass

    def play_game(self) -> np.ndarray:
        while not self.play_step():
            pass
        return self._round_results.sum(axis=0)

    def play_step(self) -> bool:
        if self._turnno is None:
            self.init_next_round()
            self._turnno = 0
            self._turncnt = self._player_count * 100
            self._finishing_playeridx = None

        if self._active_playeridx is None:
            self.determine_start_player()

        if self._active_card is None:
            self.play_step_draw()
            return False
        
        self.play_step_action()

        if self._turnno < self._turncnt:
            return False

        self.conclude_round()
        self._turnno = None
        self._roundno = self._roundno + 1

        return self._round_results.sum(axis=0).max() >= 100 or self._roundno >= 20

    def calculate_valid_options(self) -> np.ndarray:
        result = np.zeros((26, ))
        if self._active_card is None:
            result[0:2] = 1
            return result

        # Swap is allowed where card is not gone
        result[2:14] = np.where(self._player_card_status[self._active_playeridx, :] != CardStatus.GONE, 1.0, 0.0)

        # Reveal is allowed where card is hidden
        result[14:26] = np.where(self._player_card_status[self._active_playeridx, :] == CardStatus.HIDDEN, 1.0, 0.0)

        return result

    def play_step_draw(self) -> None:
        # Choose between drawing a new card or taking the top discarded one
        a = self.action()
        if a == 0: # Draw
            self._active_card = self.draw()
        elif a == 1: # Take
            self._active_card = self._topdiscard
            self._topdiscard = None
        else:
            raise IllegalActionError

    def play_step_action(self) -> None:
        playeridx = self._active_playeridx

        a = self.action()

        if a < 2 or a >= 26:
            raise IllegalActionError

        swap = a < 14
        cardidx = (a-2) % 12

        if not self.validate_action(playeridx, swap, cardidx):
            raise IllegalActionError

        # Apply action
        if swap:
            old_card = self._player_card_value[playeridx, cardidx]
            self._player_card_value[playeridx, cardidx] = self._active_card
            self._player_card_status[playeridx, cardidx] = CardStatus.REVEALED
            self.discard(old_card)
        else:
            self._player_card_status[playeridx, cardidx] = CardStatus.REVEALED
            self.discard(self._active_card)
        
        self._active_card = None

        # Check if triplet is present
        # If yes, set status to "gone", value to "0" and discard
        self.check_and_handle_triplets(playeridx)

        # Check if the game is finished (and was not finished before)
        # If yes the other players only get one more turn
        if self._finishing_playeridx is None and self.check_round_finished():
            self._finishing_playeridx = playeridx
            self._turncnt = self._turnno + self._player_count

        self._turnno = self._turnno + 1
        self._active_playeridx = (playeridx + 1) % self._player_count

    def determine_start_player(self):
        # Reveal two cards for each player
        # ToDo: Let players decide
        for i in range(self._player_count):
            self._player_card_status[i, 4] = CardStatus.REVEALED
            self._player_card_status[i, 7] = CardStatus.REVEALED

        gameinfo = self.calculate_game_info()
        # Player with the highest revealed sum starts
        # ToDo: If sum is equal, keep revealing cards
        self._active_playeridx = gameinfo._values.sum(axis=1).argmax()

    def conclude_round(self):
        # Reveal all hidden cards
        self._player_card_status = np.where(
            self._player_card_status == CardStatus.HIDDEN,
            CardStatus.REVEALED,
            self._player_card_status,
        )

        # Check for triplets one last time
        for i in range(len(self._players)):
            self.check_and_handle_triplets(i)

        final_values = self._player_card_value.sum(axis=1)

        if self._finishing_playeridx is not None:
            # If finishing player does not have the lowest score, score is doubled
            # ToDo: It's also x2 if a second player has equal score. Also it is not x2 if score is negative
            if final_values[self._finishing_playeridx] > final_values.min():
                final_values[self._finishing_playeridx] = 2 * final_values[self._finishing_playeridx]

        if self._round_results is None:
            self._round_results = np.array([final_values])
        else:
            self._round_results = np.vstack((self._round_results, final_values))

    def init_next_round(self) -> None:
        self._discarded = []
        self._player_card_value = np.zeros((len(self._players), 12))
        self._player_card_status = np.zeros((len(self._players), 12))

        self._deck = START_CARD_DECK.copy()
        random.shuffle(self._deck)

        for i in range(len(self._players)):
            for j in range(12):
                self._player_card_value[i, j] = self.draw()

        self._topdiscard = self.draw()

    def check_round_finished(self) -> bool:
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
            playercnt=self._player_count,
            values=np.where(self._player_card_status == CardStatus.REVEALED, self._player_card_value, 0),
            status=self._player_card_status,
            topdis=self._topdiscard,
            turnno=self._turnno,
            finishing=self.check_round_finished(),
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
        if cardidx < 0 or cardidx > 11:
            return False

        if swap and self._player_card_status[playeridx, cardidx] == CardStatus.GONE:
            return False

        if not swap and self._player_card_status[playeridx, cardidx] != CardStatus.HIDDEN:
            return False

        return True

class PlayerCore(abc.ABC):
    _playeridx = None

    def set_playeridx(self, playeridx):
        self._playeridx = playeridx
    
    @abc.abstractmethod
    def action(self, valid: np.ndarray, cgi:CurrentGameInfo, card:int) -> int:
        pass

class Player(PlayerCore, abc.ABC):
    def action(self, valid: np.ndarray, cgi: CurrentGameInfo, card: int) -> int:
        if valid[0] > 0.5:
            take = self.choose_take_discarded(cgi)
            return 1 if take else 0
        
        swap, cardidx = self.choose_action(cgi, card)
        return cardidx + (2 if swap else 14)

    @abc.abstractmethod
    def choose_take_discarded(self, cgi:CurrentGameInfo) -> bool:
        pass

    @abc.abstractmethod
    def choose_action(self, cgi:CurrentGameInfo, card:int) -> typing.Tuple[bool, int]:
        pass

class Game(GameCore):
    _players : typing.List[Player] = None

    def __init__(self, players) -> None:
        super().__init__(len(players))
        self._players = players

        for i, p in enumerate(self._players):
            p.set_playeridx(i)

    def action(self) -> int:
        return self._players[self._active_playeridx].action(
            self.calculate_valid_options(),
            self.calculate_game_info(),
            self._active_card
        )

class RandomPlayer(PlayerCore):
    def action(self, valid: np.ndarray, cgi: CurrentGameInfo, card: int) -> int:
        return (np.random.rand(26) * valid).argmax()

if __name__ == '__main__':
    for i in range(100):
        p1 = RandomPlayer()
        p2 = RandomPlayer()
        p3 = RandomPlayer()

        g = Game([p1, p2, p3])
        final_result = g.play_game()
        print(final_result)
        print(g._round_results)
