from abc import ABC, abstractmethod
from typing import Dict, Tuple

import numpy as np


class ScreepsMultiAgentProcessor(ABC):
    """
    Processors are a class which provides post-processing methods for interpreting room states and generating rewards.
    They can be interchangeably dropped into the Screeps environment.
    """

    def __init__(self, env):
        self.env = env

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
