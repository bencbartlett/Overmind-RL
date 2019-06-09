from abc import ABC, abstractmethod
from typing import Dict, Tuple

import numpy as np


class ScreepsProcessor(ABC):
    """
    Processors are a class which provides post-processing methods for interpreting room states and generating rewards.
    They can be interchangeably dropped into the Screeps environment.
    """

    def __init__(self, env):
        self.env = env

    @abstractmethod
    def process_action(self, action: int) -> Dict:
        """
        Placeholder function for processing an action
        :param action: int, direction to move (0-7, inclusive)
        :return: JSON-formatted command to tell the creep to move
        """
        raise NotImplementedError

    @abstractmethod
    def get_observation(self, room_state: Dict) -> np.array:
        """
        Given a room state, yield the observation
        :param room_state:
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def get_reward(self, observation: np.ndarray) -> float:
        """
        Process the observation made in step() and return a reward
        :param observation: any
        :return: reward (float)
        """
        raise NotImplementedError

    @abstractmethod
    def process_state(self, state: Dict) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Returns the observation from a room given the state after running self.interface.tick()
        :param state: dict, room state
        :return: ob, reward, done, info
        """
        raise NotImplementedError
