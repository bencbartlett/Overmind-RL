import gym

from screeps_rl_env import ScreepsInterface

PATH_TO_BACKEND = "../../screeps-rl-backend/backend/server.js"


class ScreepsEnv(gym.Env):

    def __init__(self, index = 0, use_backend = False):
        self.index = index
        self.interface = ScreepsInterface(index, use_backend = use_backend)

    def get_observation(self):
        pass

    # gym.Env methods ==================================================================================================

    def step(self, action):
        pass

    def reset(self):
        """Reset the server environment"""
        self.interface.reset()

    def render(self, mode = 'human'):
        pass

    def seed(self, seed = None):
        pass

    def close(self):
        """Close child processes"""
        self.interface.close()
