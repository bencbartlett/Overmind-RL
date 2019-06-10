from typing import Dict, List

import numpy as np


class CreepAgent:
    """
    Wrapper class which tracks creep properties
    """

    def __init__(self,
                 player_index: int,
                 creep_index: int,
                 is_bot=False,
                 body: List[Dict] = None,
                 x_init=None,
                 y_init=None):
        self.player_index = player_index
        self.creep_index = creep_index
        self.is_bot = is_bot
        self.player_name = "Agent{}".format(player_index)
        self.agent_id = "{}_{}".format(self.player_name, self.creep_index)
        self.body = body
        self.x_init = x_init
        self.y_init = y_init

    def get_full_name(self, room) -> str:
        name = "{}_{}:{}".format(self.player_name, self.creep_index, room)
        if self.is_bot:
            name += "_BOT"
        return name

    def serialize(self, randomize_body=False) -> Dict:
        if randomize_body:
            body = CreepAgent.make_random_body()
        else:
            body = self.body
        return {
            "player_name": self.player_name,
            "creep_index": self.creep_index,
            "body": body,
            "x_init": self.x_init,
            "y_init": self.y_init,
            "is_bot": self.is_bot
        }

    @staticmethod
    def generate_body(attack_parts=0, ranged_attack_parts=0, heal_parts=0, move_parts=None):

        # Default move_parts is to have 1 pos/tick movespeed
        if move_parts is None:
            move_parts = attack_parts + ranged_attack_parts + heal_parts

        # Generate the body array
        body = []
        for _ in range(attack_parts):
            body.append({"type": "attack", "hits": 100})
        for _ in range(ranged_attack_parts):
            body.append({"type": "rangedAttack", "hits": 100})
        for _ in range(heal_parts):
            body.append({"type": "heal", "hits": 100})
        for _ in range(move_parts):
            body.append({"type": "move", "hits": 100})

        return body

    @staticmethod
    def make_random_body():
        attack_parts = np.random.randint(low=1, high=3 + 1)
        ranged_parts = np.random.randint(low=1, high=3 + 1)
        heal_parts = np.random.randint(low=1, high=3 + 1)
        return CreepAgent.generate_body(attack_parts, ranged_parts, heal_parts=heal_parts)


DEFAULT_AGENT_CONFIG = [CreepAgent(1, 0), CreepAgent(2, 0)]

melee_body = CreepAgent.generate_body(attack_parts=3)
ranger_body = CreepAgent.generate_body(ranged_attack_parts=3)
healer_body = CreepAgent.generate_body(heal_parts=3)
