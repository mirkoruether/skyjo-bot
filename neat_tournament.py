"""
SKYJO tournamanet by NEAT algorithm
"""

import math
import os
import typing

import neat
import tqdm
import numpy as np

import game


def normalize_card_values(values):
    return (values + 2.0) / 14.0


def normalize_card_status(status):
    return status / 2.0


class NeatPlayer(game.PlayerCore):
    _net: neat.nn.FeedForwardNetwork = None
    _gid = None

    def __init__(self, net: neat.nn.FeedForwardNetwork, gid=None) -> None:
        super().__init__()
        self._net = net
        self._gid = gid

    def action(self, valid: np.ndarray, cgi: game.CurrentGameInfo, card: int) -> int:
        if cgi.playercnt != 2:
            raise RuntimeError("1v1 me, noob!")

        xi = self.build_input(cgi, card)
        xo = self._net.activate(xi)

        return (np.array(xo) * valid).argmax()

    def build_input(self, cgi: game.CurrentGameInfo, card: int) -> np.ndarray:
        me = self._playeridx
        opponent = (self._playeridx + 1) % 2

        result = np.zeros(54)

        result[0] = cgi.turnno / 100.0
        result[1] = 1.0 if cgi.finishing else 0.0
        result[2] = 1.0 if card is not None else 0.0
        result[3] = normalize_card_values(card) if card is not None else 0.0
        result[4] = 1.0 if cgi.topdis is not None else 0.0
        result[5] = (
            normalize_card_values(cgi.topdis) if cgi.topdis is not None else 0.0
        )

        result[6:18] = normalize_card_status(cgi.status[me, :])
        result[18:30] = normalize_card_values(cgi.values[me, :])

        result[30:42] = normalize_card_status(cgi.status[opponent, :])
        result[42:54] = normalize_card_values(cgi.values[opponent, :])

        return result


class NeatTournament:
    _players: typing.List[NeatPlayer] = None
    _best_player: NeatPlayer = None
    _best_fitness: float = 0.0

    def eval_pairing(self, pairing):
        p1idx, p2idx = pairing
        g = game.Game([self._players[p1idx], self._players[p2idx]])
        results = g.play_game()
        return (p1idx, p2idx)[results.argmin()]

    def eval_genomes(self, genomes, config):
        self._players = [
            NeatPlayer(neat.nn.FeedForwardNetwork.create(genome, config), gid)
            for gid, genome in genomes
        ]

        ranking = [1.0] * len(self._players)
        rounds = int(math.log2(len(genomes)))

        active_playeridx = list(range(int(math.pow(2.0, rounds))))

        with tqdm.tqdm(total=128 + 64 + 32 + 16 + 8 + 4 + 2 + 1) as pbar:
            for r in reversed(range(rounds)):
                pairings = []
                for x in range(int(math.pow(2.0, r))):
                    pairings.append((active_playeridx.pop(), active_playeridx.pop()))
                active_playeridx = []

                # ToDo: Parallel
                for pairing in pairings:
                    winneridx = self.eval_pairing(pairing)
                    pbar.update(1.0)
                    ranking[winneridx] += 1.0
                    active_playeridx.append(winneridx)

        final_winneridx = active_playeridx.pop()

        offset = 0.0
        if self._best_player is None:
            self._best_player = self._players[final_winneridx]
            self._best_fitness = ranking[final_winneridx]
        else:
            # Winners plays against the last generation's winner
            g = game.Game([self._best_player, self._players[final_winneridx]])
            if g.play_game().argmin() == 0:  # Old winner wins
                offset = self._best_fitness - ranking[final_winneridx] - 1.0
            else:  # New winner wins
                offset = self._best_fitness - ranking[final_winneridx] + 1.0
                self._best_player = self._players[final_winneridx]
                self._best_fitness = ranking[final_winneridx] + offset

        for (i, (gid, genome)) in enumerate(genomes):
            genome.fitness = ranking[i] + offset

    def run(self, config_file):
        config = neat.Config(
            neat.DefaultGenome,
            neat.DefaultReproduction,
            neat.DefaultSpeciesSet,
            neat.DefaultStagnation,
            config_file,
        )

        p = neat.Population(config)

        p.add_reporter(neat.StdOutReporter(True))
        stats = neat.StatisticsReporter()
        p.add_reporter(stats)
        p.add_reporter(neat.Checkpointer(5))

        winner = p.run(self.eval_genomes, 100)
        print(f"\nBest genome:\n{winner}")


if __name__ == "__main__":
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, "neat-config")
    NeatTournament().run(config_path)
