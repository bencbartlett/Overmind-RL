from typing import Dict

import numpy as np
from gym.spaces import Dict as DictSpace, Discrete, Box, Tuple

from screeps_rl_env.processors_multiagent import ScreepsMultiAgentProcessor


class CombatMultiAgentProcessor(ScreepsMultiAgentProcessor):
    """
    Train a creep to approach the other creep in the room using base movement intents
    """

    @staticmethod
    def get_spaces(agents):

        creep_features = DictSpace({
            "xy": Box(low=0, high=49, shape=(2,), dtype=np.uint8),
            "dxdy": Box(low=-49, high=49, shape=(2,), dtype=np.int8),
            "hits": Box(low=0, high=100 * 50, shape=(1,), dtype=np.uint16),
            # "hits_max": Box(low=0, high=100 * 50, shape=(1,), dtype=np.uint16),
            "hits_frac": Box(low=0, high=1, shape=(1,), dtype=np.float16),
            "attack_potential": Box(low=0, high=50, shape=(1,), dtype=np.uint16),
            "ranged_attack_potential": Box(low=0, high=50, shape=(1,), dtype=np.uint16),
            "heal_potential": Box(low=0, high=50, shape=(1,), dtype=np.uint16),
        })

        observation_space = Tuple([creep_features] * len(agents))
        action_space = Discrete(2)

        return observation_space, action_space

    def process_action(self, action, agent_id):
        creep_name = self.env.agents_dict[agent_id].get_full_name(self.env.room)

        if action == 0:
            action_type = 'approachHostiles'
        elif action == 1:
            action_type = 'avoidHostiles'
        else:
            raise ValueError(f"Action {action} for agent_id {agent_id} is not valid!")

        return {creep_name: [[action_type, None]]}

    def get_features(self, creep: Dict, me: Dict) -> Dict:
        """
        Gets the feature vector of the creep
        :param creep: dictionary with all creep properties
        :param me: creep to compare to for computing various parameters, e.g. dx, dy
        :return: features for the creep
        """
        x, y = creep["x"], creep["y"]
        dx, dy = x - me["x"], y - me["y"]
        hits, hits_max = creep["hits"], creep["hitsMax"]
        hits_frac = hits / hits_max

        body = creep["body"]

        # Compute potentials
        potentials = {}
        for part in body:
            if part["hits"] > 0:
                potentials[part["type"]] = potentials.get(part["type"], 0) + 1

        attack_potential = potentials.get("attack", 0)
        ranged_attack_potential = potentials.get("rangedAttack", 0)
        heal_potential = potentials.get("heal", 0)

        return {
            "xy": np.array([x, y]),
            "dxdy": np.array([dx, dy]),
            "hits": np.array([hits]),
            # "hits_max": hits_max,
            "hits_frac": np.array([hits_frac]),
            "attack_potential": np.array([attack_potential]),
            "ranged_attack_potential": np.array([ranged_attack_potential]),
            "heal_potential": np.array([heal_potential]),
        }

        # return x, y, dx, dy, hits, hits_max, hits_frac, attack_potential, ranged_attack_potential, heal_potential

    def get_observation(self, room_state, agent_id):
        room_objects = room_state["roomObjects"]
        event_log = room_state["eventLog"]

        tombstones_present = any(filter(lambda obj: obj['type'] == 'tombstone', room_objects))

        if tombstones_present:
            print(list(filter(lambda obj: obj['type'] == 'tombstone', room_objects)))
            return None

        enemies, allies, me = self.get_enemies_allies_me(room_objects, agent_id)
        all_creeps = [*enemies, *allies, me]
        return [self.get_features(creep, me) for creep in all_creeps]
        # return np.array()

        # return np.concatenate([
        #     self.get_features(creep, me) for creep in [*enemies, *allies, me]
        # ])

    def get_reward(self, room_state, agent_id):

        DISTANCE_PENALTY = -0.001
        DAMAGE_REWARD = 1 / 100 * 1
        ENEMY_DEATH_REWARD = 10
        ALLIED_DEATH_PENALTY = -5

        reward = 0

        room_objects = room_state["roomObjects"]
        event_log = room_state["eventLog"]

        enemies, allies, me = self.get_enemies_allies_me(room_objects, agent_id)

        # Add distance penalties
        for creep in [*enemies, *allies]:
            dx, dy = self.get_features(creep, me)["dxdy"]
            reward += DISTANCE_PENALTY * max(abs(dx), abs(dy))

        # Add damage rewards
        my_creep_id = me["_id"]
        reward += DAMAGE_REWARD * self.get_damage_done_last_tick(event_log, my_creep_id)

        # Add death rewards
        reward += ENEMY_DEATH_REWARD * len(self.get_enemy_deaths(event_log, agent_id))
        reward += ALLIED_DEATH_PENALTY * len(self.get_allied_deaths(event_log, agent_id))

        return reward

    def process_state(self, room_state, agent_id):
        """Returns the observation from a room given the state after running self.interface.tick()"""
        ob = self.get_observation(room_state, agent_id)

        if ob is not None:
            self.prev_ob[agent_id] = ob
            return ob, self.get_reward(room_state, agent_id), False, {}
        else:
            return self.prev_ob[agent_id], 0, True, {}
