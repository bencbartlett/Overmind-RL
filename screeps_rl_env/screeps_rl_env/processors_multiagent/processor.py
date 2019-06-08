from abc import ABC, abstractmethod
from typing import Dict, Tuple, List

import numpy as np


class ScreepsMultiAgentProcessor(ABC):
    """
    Processors are a class which provides post-processing methods for interpreting room states and generating rewards.
    They can be interchangeably dropped into the Screeps environment.
    """

    def __init__(self, env):
        from screeps_rl_env import ScreepsMultiAgentEnv  # local import needed to prevent circular dependencies
        self.env: ScreepsMultiAgentEnv = env

    def get_creeps(self, room_objects: List) -> List[Dict]:
        """
        Get a list of room objects which are creeps
        :param room_objects: room objects for the environment room
        :return: objects which are creeps
        """
        return list(filter(lambda obj: obj['type'] == 'creep', room_objects))

    def get_allies(self, room_objects: List, agent_id: str, include_self=False) -> List[Dict]:
        """
        Returns a list of allied creeps given room objects
        :param room_objects: room objects for the environment room
        :param agent_id: id of the agent to be compared to
        :param include_self: whether or not to include the agent itself in the list
        :return: all allied creeps
        """
        all_creeps = self.get_creeps(room_objects)

        creep = self.env.agents_dict[agent_id]
        creep_name = creep.get_full_name(self.env.room)
        creep_owner = creep.player_name

        if include_self:
            return list(filter(lambda creep: creep['username'] == creep_owner, all_creeps))
        else:
            return list(filter(lambda creep: creep['username'] == creep_owner and
                                             creep['name'] != creep_name,
                               all_creeps))

    def get_enemies(self, room_objects: List, agent_id: str) -> List[Dict]:
        """
        Returns a list of enemy creeps given room objects
        :param room_objects: room objects for the environment room
        :param agent_id: id of the agent to be compared to
        :return: all enemy creeps
        """
        all_creeps = self.get_creeps(room_objects)

        owner = self.env.agents_dict[agent_id].player_name

        return list(filter(lambda creep: creep['username'] == owner, all_creeps))

    def get_enemies_allies_me(self, room_objects: List, agent_id: str) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        Given room objects and an agent id, return a tuple of (enemy creeps, allied creeps, self) sorted by name
        :param room_objects: room objects for the environment room
        :param agent_id: id of the agent to be compared to
        :return: all enemy creeps
        """

        creep = self.env.agents_dict[agent_id]
        creep_name = creep.get_full_name(self.env.room)
        creep_owner = creep.player_name

        all_creeps = self.get_creeps(room_objects)

        enemies, allies, me = [], [], None

        for creep in all_creeps:
            if creep['username'] != creep_owner:
                enemies.append(creep)
            else:
                if creep['name'] != creep_name:
                    allies.append(creep)
                else:
                    me = creep

        enemies.sort(key=lambda creep: creep['name'])
        allies.sort(key=lambda creep: creep['name'])

        return enemies, allies, me

    @abstractmethod
    def process_state(self, room_state: Dict, agent_id: str) -> np.array:
        """
        Process the room state
        :param room_state: the state of the room
        :param agent_id: the name of the creep to receive the processed input
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def process_action(self, action: int, agent_id: str) -> Dict:
        """
        Placeholder function for processing an action
        :param action: int, direction to move (0-7, inclusive)
        :param agent_id: the name of the creep to receive the processed input
        :return: JSON-formatted command to tell the creep to move
        """
        raise NotImplementedError

    @abstractmethod
    def process_reward(self, observation: np.ndarray, agent_id: str) -> float:
        """
        Process the observation made in step() and return a reward
        :param observation: any
        :param agent_id: the name of the creep to receive the processed input
        :return: reward (float)
        """
        raise NotImplementedError

    @abstractmethod
    def process_observation(self, state: Dict, agent_id: str) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Returns the observation from a room given the state after running self.interface.tick()
        :param state: dict, room state
        :param agent_id: the name of the creep to receive the processed input
        :return: ob, reward, done, info
        """
        raise NotImplementedError
