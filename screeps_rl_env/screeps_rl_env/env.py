from time import sleep
from typing import Type, Union, Dict

import gym
import numpy as np
from ray.rllib.env import EnvContext

from screeps_rl_env.interface import ScreepsInterface
from screeps_rl_env.processors import ApproachProcessor, ScreepsProcessor
from screeps_rl_env.utils import running_on_laptop

if running_on_laptop():
    import matplotlib.pyplot as plt
else:  # fix for crash when running on gcompute machines
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt


class ScreepsEnv(gym.Env):

    def __init__(self,
                 env_config: Union[EnvContext, Dict],
                 processor: Type[ScreepsProcessor] = ApproachProcessor,
                 worker_index: int = None,
                 vector_index: int = None,
                 interface: ScreepsInterface = None,
                 use_backend: bool = False,
                 use_viewer: bool = False):

        self.processor = processor(self)

        self.worker_index = worker_index if worker_index is not None else env_config.worker_index
        self.vector_index = vector_index if vector_index is not None else env_config.vector_index

        print(f"worker_index: {self.worker_index}, vector_index: {self.vector_index}")

        self.username = "Agent1"  # TODO: hardcoded for now

        self.use_backend = use_backend
        self.client_connected = False

        if interface is None:
            print('starting interface with worker index {}'.format(self.worker_index))
            self.interface = ScreepsInterface(self.worker_index, use_backend=self.use_backend)
            self.uses_external_interface = False
        else:
            self.interface = interface
            self.uses_external_interface = True

        self.use_viewer = use_viewer
        self.fig = None

        # Request a new mini-environment from the screeps interface. Returns a reference to the environment's room name
        self.room = self.interface.add_env(self.vector_index)

        # Reset if running in non-vector mode (allow vector env to reset if interface is specified)
        if not self.uses_external_interface:
            self.interface.reset()

        # TODO: these are placeholder spaces. obs space is x,y of self and enemy, act space is movement in 8 directions
        self.observation_space = gym.spaces.MultiDiscrete([50, 50, 50, 50])
        self.action_space = gym.spaces.Discrete(8)
        self.state = None

    # gym.Env methods ==================================================================================================

    def step(self, action):
        """
        The agent takes a step in the environment.
        Parameters
        ----------
        action : int
        Returns
        -------
        ob, reward, episode_over, info : tuple
            ob (object) :
                an environment-specific object representing your observation of
                the environment.
            reward (float) :
                amount of reward achieved by the previous action. The scale
                varies between environments, but the goal is always to increase
                your total reward.
            episode_over (bool) :
                whether it's time to reset the environment again. Most (but not
                all) tasks are divided up into well-defined episodes, and done
                being True indicates the episode has terminated. (For example,
                perhaps the pole tipped too far, or you lost your last life.)
            info (dict) :
                 diagnostic information useful for debugging. It can sometimes
                 be useful for learning (for example, it might contain the raw
                 probabilities behind the environment's last state change).
                 However, official evaluations of your agent are not allowed to
                 use this for learning.
        """
        command = self.processor.process_action(action)
        self.interface.send_action(command, self.username)

        self.interface.tick()

        self.state = self.interface.get_room_state(self.room)

        return self.processor.process_observation(self.state)

    def reset(self):
        """Reset the server environment"""
        self.interface.reset()
        self.interface.tick()
        state = self.interface.get_room_state(self.room)
        return self.processor.process_state(state)

    def reset_soft(self):
        self.interface.reset_room(self.room)

    def render(self, mode='human'):

        if mode == 'human':
            if not self.use_backend:
                print("Run the environment with use_backend=True to connect the Screeps client")
                return
            if not self.client_connected:
                _ = input("Connect the Screeps client and press enter when ready to proceed.")
                self.client_connected = True
            sleep_time = 0.1
            sleep(sleep_time)

        elif mode == 'rgb_array':
            arr = np.zeros((50, 50, 3), dtype=int)
            if self.state is None:
                return arr
            terrain = self.state["terrain"]
            room_objects = self.state["roomObjects"]

            plain_color = np.array([43, 43, 43])
            swamp_color = np.array([41, 42, 24])
            wall_color = np.array([17, 17, 17])

            # Color terrain
            for y in np.arange(50):
                for x in np.arange(50):
                    tile = terrain[y][x]
                    if tile == 2:
                        color = swamp_color
                    elif tile == 1:
                        color = wall_color
                    else:
                        color = plain_color

                    arr[y][x][...] = color

            # Color creeps
            for obj in room_objects:
                if obj['type'] == 'creep':
                    x, y = obj['x'], obj['y']
                    if 'Agent1' in obj['name']:
                        arr[y][x][...] = np.array([0, 0, 255])
                    elif 'Agent2' in obj['name']:
                        arr[y][x][...] = np.array([255, 0, 0])

            if self.use_viewer:
                if self.fig is None:
                    self.fig = plt.figure(figsize=(5, 5))
                # self.viewer.imshow(arr)
                plt.imshow(arr)
                plt.pause(0.05)

            return arr

    def seed(self, seed=None):
        pass  # TODO: do we need this?

    def close(self):
        """Close child processes"""
        if self.use_viewer:
            plt.close()

        if not self.uses_external_interface:
            self.interface.close()
