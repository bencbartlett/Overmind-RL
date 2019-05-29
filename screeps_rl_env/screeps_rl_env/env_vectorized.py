import json

import gym
import numpy as np
from ray.rllib import VectorEnv

from screeps_rl_env.env import ScreepsEnv
from screeps_rl_env.interface import ScreepsInterface


class ScreepsVectorEnv(VectorEnv):

    def __init__(self,
                 env_config,
                 num_envs = 10,
                 worker_index = None,
                 use_backend = False):

        print("ENV_CONFIG:")
        print(env_config)

        print(f"worker_index: {env_config.worker_index}, vector_index: {env_config.vector_index}")

        self.worker_index = worker_index if worker_index is not None else env_config.worker_index

        print('Starting interface with worker index {}'.format(self.worker_index))
        self.interface = ScreepsInterface(self.worker_index, use_backend = use_backend, reset_on_start = False)

        self.envs = []
        for vector_index in range(num_envs):
            self.envs.append(ScreepsEnv(env_config = env_config,
                                        worker_index = worker_index,
                                        vector_index = vector_index,
                                        interface = self.interface,
                                        use_backend = use_backend))

        self.observation_space = self.envs[0].observation_space
        self.action_space = self.envs[0].action_space

    def vector_reset(self):
        """Resets all environments.

        Returns:
            obs (list): Vector of observations from each environment.
        """
        self.interface.reset()
        self.interface.tick()
        states_all = self.interface.get_all_room_states()
        return [env.process_state(states_all[env.vector_index]) for env in self.envs]

    def reset_at(self, index):
        """Resets a single environment.

        Returns:
            obs (obj): Observations from the resetted environment.
        """
        room = self.envs[index].room
        self.interface.reset_room(room)
        state = self.interface.get_room_state(room)
        return self.envs[index].process_state(state)

    def vector_step(self, actions):
        """Vectorized step.

        Arguments:
            actions (list): Actions for each env.

        Returns:
            obs (list): New observations for each env.
            rewards (list): Reward values for each env.
            dones (list): Done values for each env.
            infos (list): Info values for each env.
        """

        raise NotImplementedError

    def close(self):
        """Close child processes"""
        self.interface.close()
