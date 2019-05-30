import gym
import numpy as np

from screeps_rl_env.interface import ScreepsInterface

PATH_TO_BACKEND = "../../screeps-rl-backend/backend/server.js"


def simple_reward(creep1xy, creep2xy):
    """Simple reward that tells creeps to move toward each other"""
    x1, y1 = creep1xy
    x2, y2 = creep2xy
    return 50 - np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


class ScreepsEnv(gym.Env):

    def __init__(self,
                 env_config = None,
                 worker_index = None,
                 vector_index = None,
                 interface = None,
                 use_backend = False):

        # print("ENV_CONFIG:")
        # pprint(env_config)

        self.worker_index = worker_index if worker_index is not None else env_config.worker_index
        self.vector_index = vector_index if vector_index is not None else env_config.vector_index

        print(f"worker_index: {self.worker_index}, vector_index: {self.vector_index}")

        self.username = "Agent1"  # TODO: hardcoded for now

        if interface is None:
            print('starting interface with worker index {}'.format(self.worker_index))
            self.interface = ScreepsInterface(self.worker_index, use_backend = use_backend)
        else:
            self.interface = interface

        # Request a new mini-environment from the screeps interface. Returns a reference to the environment's room name
        self.room = self.interface.add_env(self.vector_index)

        # Reset if running in non-vector mode (allow vector env to reset if interface is specified)
        if interface is None:
            self.interface.reset()

        # TODO: these are placeholder spaces. obs space is x,y of self and enemy, act space is movement in 8 directions
        self.observation_space = gym.spaces.MultiDiscrete([50, 50, 50, 50])
        self.action_space = gym.spaces.Discrete(8)

    def process_state(self, room_state):
        terrain = room_state["terrain"]
        room_objects = room_state["roomObjects"]
        event_log = room_state["eventLog"]

        my_creep_name = "Agent1_{}_{}".format(self.vector_index, 0)
        enemy_creep_name = "Agent2_{}_{}".format(self.vector_index, 0)

        enemy_creeps = list(filter(lambda obj: obj["type"] == "creep" and
                                               obj["name"] == enemy_creep_name, room_objects))
        enemy_creep = enemy_creeps[0] if len(enemy_creeps) > 0 else None

        my_creeps = list(filter(lambda obj: obj["type"] == "creep" and
                                            obj["name"] == my_creep_name, room_objects))
        my_creep = my_creeps[0] if len(my_creeps) > 0 else None

        if enemy_creep is not None and my_creep is not None:
            return np.array([my_creep["x"], my_creep["y"], enemy_creep["x"], enemy_creep["y"]])
        else:
            return np.array([25, 25, 25, 25]) # TODO: placeholder

    def process_action(self, action):
        """
        Placeholder function for processing an action
        :param action: int, direction to move (0-7, inclusive)
        :return: JSON-formatted command to tell the creep to move
        """
        creep_name = "Agent1_{}_{}".format(self.vector_index, 0)
        return {creep_name: [["move", int(action) + 1]]}

    def process_reward(self, observation):
        """
        Process the observation made in step() and return a reward
        :param observation: any
        :return: reward (float)
        """
        my_x, my_y, foe_x, foe_y = observation
        return simple_reward((my_x, my_y), (foe_x, foe_y))

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
        command = self.process_action(action)
        self.interface.send_action(command, self.username)

        self.interface.tick()

        state = self.interface.get_room_state(self.room)

        ob = self.process_state(state)

        if ob is not None:
            return ob, self.process_reward(ob), False, {}
        else:
            return ob, 0, True, {}

    def reset(self):
        """Reset the server environment"""
        self.interface.reset()
        self.interface.tick()
        state = self.interface.get_room_state(self.room)
        return self.process_state(state)

    def reset_soft(self):
        self.interface.reset_room(self.room)

    def render(self, mode = 'human'):
        print("Run the environment with use_backend=True to connect the Screeps client")

    def seed(self, seed = None):
        pass  # TODO: do we need this?

    def close(self):
        """Close child processes"""
        self.interface.close()
