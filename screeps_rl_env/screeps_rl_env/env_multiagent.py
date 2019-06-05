from time import sleep
from typing import Type, Union, Dict, List

import gym
import matplotlib.pyplot as plt
import numpy as np
from ray.rllib import MultiAgentEnv
from ray.rllib.env import EnvContext
from screeps_rl_env.interface import ScreepsInterface
from screeps_rl_env.processors_multiagent import ScreepsMultiAgentProcessor, ApproachMultiAgentProcessor

PATH_TO_BACKEND = "../../screeps-rl-backend/backend/server.js"


class CreepAgent:
    """
    Wrapper class which tracks creep properties
    """

    def __init__(self, player_index: int, creep_index: int, body: List[Dict] = None, x_init = None, y_init = None):
        self.player_index = player_index
        self.player_name = "Agent{}".format(player_index)
        self.creep_index = creep_index
        self.agent_id = "{}_{}".format(self.player_name, self.creep_index)
        self.body = body
        self.x_init = x_init
        self.y_init = y_init

    def get_full_name(self, room) -> str:
        return "{}_{}:{}".format(self.player_name, self.creep_index, room)

    def serialize(self) -> Dict:
        return {
            "player_name": self.player_name,
            "creep_index": self.creep_index,
            "body"       : self.body,
            "x_init"     : self.x_init,
            "y_init"     : self.y_init,
        }


DEFAULT_AGENT_CONFIG = [CreepAgent(1, 0), CreepAgent(2, 0)]


class ScreepsMultiAgentEnv(MultiAgentEnv):

    def __init__(self,
                 env_config: Union[EnvContext, Dict],
                 agents: List[CreepAgent] = DEFAULT_AGENT_CONFIG,
                 processor: Type[ScreepsMultiAgentProcessor] = ApproachMultiAgentProcessor,
                 worker_index: int = None,
                 vector_index: int = None,
                 interface: ScreepsInterface = None,
                 use_backend: bool = False,
                 use_viewer: bool = False):

        self.processor = processor(self)

        # Set worker and vector indices
        self.worker_index = worker_index if worker_index is not None else env_config.worker_index
        self.vector_index = vector_index if vector_index is not None else env_config.vector_index
        print(f"worker_index: {self.worker_index}, vector_index: {self.vector_index}")

        # Register agents
        self.agents = agents
        self.agents_dict = {agent.agent_id: agent for agent in self.agents}

        # Backend initialization, usually ignored
        self.use_backend = use_backend
        self.client_connected = False

        # Viewer is used for render(mode='rgb_array')
        self.use_viewer = use_viewer
        self.fig = None

        # Instantiate interface if one is not provided
        if interface is None:
            print('starting interface with worker index {}'.format(self.worker_index))
            self.interface = ScreepsInterface(self.worker_index, use_backend = self.use_backend)
            self.uses_external_interface = False
        else:
            self.interface = interface
            self.uses_external_interface = True

        # Request a new mini-environment from the screeps interface. Returns a reference to the environment's room name
        self.room = self.interface.add_env(self.vector_index)
        self.time = 0

        # Reset if running in non-vector mode (allow vector env to reset if interface is specified)
        if not self.uses_external_interface:
            self.interface.reset()
            self.time = self.interface.tick()

        # TODO: hardcoded
        self.observation_space, self.action_space = ScreepsMultiAgentEnv.get_spaces(self.agents)

        self.state = None

        # Reset to get desired creep config
        self.reset()

    @staticmethod
    def get_spaces(agents: List[CreepAgent]):
        """
        Yields the observation and action spaces; convenient for fetching spaces without instantiatng an environment
        :param agents: list of agents that would instantiate the ScreepsMultiAgentEnv
        :return: observation_space, action_space
        """
        observation_space = gym.spaces.MultiDiscrete((50, 50) * len(agents))
        action_space = gym.spaces.Discrete(8)
        return observation_space, action_space

    # def reset(self):
    #     """Resets the env and returns observations from ready agents.
    #
    #     Returns:
    #         obs (dict): New observations for each ready agent.
    #     """
    #     self.interface.reset()
    #     self.interface.tick()
    #     state = self.interface.get_room_state(self.room)
    #     return self.processor.process_state(state)

    def reset(self):
        self.interface.reset_room(self.room, [agent.serialize() for agent in self.agents])
        self.time = self.interface.tick()
        state = self.interface.get_room_state(self.room)
        return {id: self.processor.process_state(state, id) for id in self.agents_dict.keys()}

    def step(self, action_dict: Dict):
        """Returns observations from ready agents.

        The returns are dicts mapping from agent_id strings to values. The
        number of agents in the env can vary over time.

        Returns
        -------
            obs (dict): New observations for each ready agent.
            rewards (dict): Reward values for each ready agent. If the
                episode is just started, the value will be None.
            dones (dict): Done values for each ready agent. The special key
                "__all__" (required) is used to indicate env termination.
            infos (dict): Optional info values for each agent id.
        """

        # print(f"action_dict: {action_dict}")

        # build a dictionary of {username: {creepName: [list of actions and arguments] } }
        all_actions = {}
        for id, action in action_dict.items():
            agent = self.agents_dict[id]
            if all_actions.get(agent.player_name) is None:
                all_actions[agent.player_name] = {}
            all_actions[agent.player_name].update(self.processor.process_action(action, id))

        # send actions to screeps environment
        self.interface.send_all_actions(all_actions)

        # Run the tick
        self.time = self.interface.tick()

        # Return processed state
        self.state = self.interface.get_room_state(self.room)

        obs, rewards, dones, infos = {}, {}, {}, {}
        for id in action_dict.keys():
            obs[id], rewards[id], dones[id], infos[id] = self.processor.process_observation(self.state, id)
        dones["__all__"] = any(dones.values())
        # assert obs[id] is not None, f"Obs is none! self.time={self.time}"

        # print(f"Returns: {obs} | {rewards} | {dones} | {infos}")

        return obs, rewards, dones, infos

    def render(self, mode = 'rgb_array'):

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
            arr = np.zeros((50, 50, 3), dtype = int)
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
                    self.fig = plt.figure(figsize = (5, 5))
                # self.viewer.imshow(arr)
                plt.imshow(arr)
                plt.pause(0.05)

            return arr

    def seed(self, seed = None):
        pass  # TODO: do we need this?

    def close(self):
        """Close child processes"""
        if self.use_viewer:
            plt.close()

        if not self.uses_external_interface:
            self.interface.close()