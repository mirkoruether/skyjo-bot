"""
"""

import typing
import game

class ConsolePlayer(game.Player):
    def choose_take_discarded(self, cgi: game.CurrentGameInfo) -> bool:
        self.print_info(cgi)
        return str(input(f"Top discarded car is {cgi._topdis:02.0f}. If you want to take it type 'y': ")).upper() == 'Y'

    def choose_action(self, cgi: game.CurrentGameInfo, card: int) -> typing.Tuple[bool, int]:
        print(f"Active card is {card:02.0f}")
        swap = str(input("Do you want to use this card? Type 'y': ")).upper() == 'Y'
        if swap:
            cardidx = int(input("Choose new position: "))
        else:
            cardidx = int(input("Choose card to reveal: "))
        return swap, cardidx

    def print_info(self, cgi: game.CurrentGameInfo):
        print(f"--- Board Player {self._playeridx:02.0f} ---")
        for i in range(12):
            val = cgi._values[self._playeridx, i]
            stat = cgi._status[self._playeridx, i]
            if stat == game.CardStatus.HIDDEN:
                card = " ?"
            elif stat == game.CardStatus.GONE:
                card = " X"
            else:
                card = f"{val:02.0f}"
            print(card, end=' ' if i%3 != 2 else None)
        print(f"-----------------------")

if __name__ == '__main__':
    p = ConsolePlayer()
    g = game.GamePlayers([p])
    print(g.play_game())
