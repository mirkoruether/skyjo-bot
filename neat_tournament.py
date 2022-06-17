"""
SKYJO tournamanet by NEAT algorithm
"""

import os
import neat

import numpy as np

import game


def normalize_card_values(values):
    return (values + 2.0) / 14.0

def normalize_card_status(status):
    return status / 2.0

class NeatPlayer(game.PlayerCore):
    _net: neat.FeedForwardNetwork = None
    _gid = None

    def __init__(self, net: neat.FeedForwardNetwork, gid=None) -> None:
        super().__init__()
        self._net = net
        self._gid = gid
    
    def action(self, valid: np.ndarray, cgi: game.CurrentGameInfo, card: int) -> int:
        if cgi._playercnt != 2:
            raise RuntimeError("1v1 me, noob!")

        xi = self.build_input(cgi, card)
        xo = self._net.activate(xi)

        return (np.array(xo) * valid).argmax()

    def build_input(self, cgi: game.CurrentGameInfo, card: int) -> np.ndarray:
        me = self._playeridx
        opponent = (self._playeridx + 1) % 2

        result = np.zeros(54)

        result[0] = cgi._turnno / 100.0
        result[1] = 1.0 if cgi._finishing else 0.0
        result[2] = 1.0 if card is not None else 0.0
        result[3] = normalize_card_values(card) if card is not None else 0.0
        result[4] = 1.0 if cgi._topdis is not None else 0.0
        result[5] = normalize_card_values(cgi._topdis) if cgi._topdis is not None else 0.0

        result[6:18] = normalize_card_status(cgi._status[me, :])
        result[18:30] = normalize_card_values(cgi._values[me, :])

        result[30:42] = normalize_card_status(cgi._status[opponent, :])
        result[42:54] = normalize_card_values(cgi._values[opponent, :])

        return result

def eval_genomes(genomes, config):
    players = [NeatPlayer(neat.nn.FeedForwardNetwork.create(genome, config), gid) for gid, genome in genomes]

    for gid, genome in genomes:
        genome.fitness = 1.0

    # Tournament goes here

def run(config_file):
    config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                         neat.DefaultSpeciesSet, neat.DefaultStagnation,
                         config_file)

    p = neat.Population(config)

    p.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    p.add_reporter(stats)
    p.add_reporter(neat.Checkpointer(5))

    winner = p.run(eval_genomes, 300)
    print('\nBest genome:\n{!s}'.format(winner))

if __name__ == '__main__':
    # Determine path to configuration file. This path manipulation is
    # here so that the script will run successfully regardless of the
    # current working directory.
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, 'neat-config')
    run(config_path)

