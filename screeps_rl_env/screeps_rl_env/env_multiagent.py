from time import sleep
from typing import Type, Union, Dict, List

import numpy as np
from ray.rllib import MultiAgentEnv
from ray.rllib.env import EnvContext

from screeps_rl_env.creep_agent import CreepAgent, DEFAULT_AGENT_CONFIG
from screeps_rl_env.interface import ScreepsInterface
from screeps_rl_env.processors_multiagent import ScreepsMultiAgentProcessor, ApproachMultiAgentProcessor
from screeps_rl_env.utils import running_on_laptop

if running_on_laptop():
    import matplotlib.pyplot as plt
else:  # fix for crash when running on gcompute machines
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt


class ScreepsMultiAgentEnv(MultiAgentEnv):

    def __init__(self,
                 env_config: Union[EnvContext, Dict],
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
        if 'agents' not in env_config: print("USING DEFAULT AGENTS")
        self.agents_all = env_config.get('agents', DEFAULT_AGENT_CONFIG)
        self.agents_controllable = list(filter(lambda agent: not agent.is_bot, self.agents_all))
        self.agents_dict = {agent.agent_id: agent for agent in self.agents_controllable}

        # Whether to randomize the body compositions
        self.randomize_bodies = env_config.get('randomize_bodies', True)

        # Backend initialization, usually ignored
        self.use_backend = use_backend
        self.client_connected = False

        # Viewer is used for render(mode='rgb_array')
        self.use_viewer = use_viewer
        self.fig = None

        # Instantiate interface if one is not provided
        if interface is not None:
            self.interface = interface
            print('Using existing interface {} with worker_index {} and vector_index {}'.format(
                self.interface, self.worker_index, self.vector_index))
            self.uses_external_interface = True
        else:
            print('Starting interface with worker_index {} and vector_index {}'.format(
                self.worker_index, self.vector_index))
            self.interface = ScreepsInterface(self.worker_index, use_backend=self.use_backend)
            self.uses_external_interface = False

        # Request a new mini-environment from the screeps interface. Returns a reference to the environment's room name
        self.room = self.interface.add_env(self.vector_index)
        self.time = 0

        self.id_ownership = {}  # map of { [game id]: user owning the object }
        self.user_id_to_username = {}  # map of { [game user hash]: username }
        self.state = None

        # Reset if running in non-vector mode (allow vector env to reset if interface is specified)
        if not self.uses_external_interface:
            # Perform a hard reset, allow two ticks, then reset the room state
            self.interface.reset()
            for _ in range(2):
                self.time = self.interface.tick()
            self.reset()

        self.observation_space, self.action_space = ScreepsMultiAgentEnv.get_spaces(self.agents_all,
                                                                                    processor=processor)

    @staticmethod
    def get_spaces(agents: List[CreepAgent],
                   processor: Type[ScreepsMultiAgentProcessor] = ApproachMultiAgentProcessor):
        return processor.get_spaces(agents)

    def reset(self):
        """
        Reset the room to the configured state and rebuild mappings of creeps -> user and user_id -> user
        :return: observations for each (controllable) agent
        """
        creep_config = [agent.serialize(randomize_body=self.randomize_bodies) for agent in self.agents_all]
        self.interface.reset_room(self.room, creep_config)

        self.state = self.interface.get_room_state(self.room)
        room_objects = self.state["roomObjects"]

        self.id_ownership = {}
        self.user_id_to_username = {}

        for obj in room_objects:
            id = obj.get("_id")
            owner = obj.get("username")
            user_id = obj.get("user")
            if id is not None and owner is not None:
                self.id_ownership[id] = owner
            if user_id is not None and owner is not None:
                self.user_id_to_username[user_id] = owner

        return {id: self.processor.get_observation(self.state, id) for id in self.agents_dict.keys()}

    def step_pre_tick(self, action_dict: Dict):
        # build a dictionary of {username: {creepName: [list of actions and arguments] } }
        processed_actions = {}
        for id, action in action_dict.items():
            agent = self.agents_dict[id]
            if processed_actions.get(agent.player_name) is None:
                processed_actions[agent.player_name] = {}
            processed_actions[agent.player_name].update(self.processor.process_action(action, id))

        return processed_actions

    def step_post_tick(self, action_dict: Dict, room_state: Dict):

        obs, rewards, dones, infos = {}, {}, {}, {}
        for id in action_dict.keys():
            obs[id], rewards[id], dones[id], infos[id] = self.processor.process_state(room_state, id)
        dones["__all__"] = all(dones.values())

        return obs, rewards, dones, infos

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

        all_actions = self.step_pre_tick(action_dict)

        # send actions to screeps environment
        self.interface.send_all_actions(all_actions)

        # Run the tick
        self.time = self.interface.tick()

        # Return processed state
        self.state = self.interface.get_room_state(self.room)

        return self.step_post_tick(action_dict, self.state)

    def render(self, mode=None):

        mode = 'human' if self.use_backend else 'rgb_array'

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
