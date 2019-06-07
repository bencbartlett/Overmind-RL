from typing import Dict, Union, List

from ray.rllib import BaseEnv, MultiAgentEnv
from ray.rllib.env import EnvContext
from ray.rllib.env.base_env import _MultiAgentEnvState
from screeps_rl_env import ScreepsMultiAgentEnv, ScreepsInterface, CreepAgent


class ScreepsMultiAgentVectorEnv(BaseEnv):

    def __init__(self,
                 env_config: Union[EnvContext, Dict],
                 num_envs: int = 1,
                 interface: ScreepsInterface = None,
                 use_backend: bool = False,
                 use_viewer: bool = False):

        self.worker_index = env_config.worker_index

        # Backend initialization, usually ignored
        self.use_backend = use_backend

        # Viewer is used for render(mode='rgb_array')
        self.use_viewer = use_viewer

        if interface is None:
            print(f"==> Starting new ScreepsInterface with worker_index={self.worker_index} <==")
            self.interface = ScreepsInterface(self.worker_index)
        else:
            print('Using existing interface {} with worker index {}'.format(self.interface, self.worker_index))
            self.interface = interface

        # Instantiate environments
        self.num_envs = num_envs
        self.envs = [
            ScreepsMultiAgentEnv(env_config,
                                 worker_index = self.worker_index,
                                 vector_index = i,
                                 interface = self.interface,
                                 use_backend = self.use_backend,
                                 use_viewer = self.use_viewer)
            for i in range(self.num_envs)
        ]
        self.envs_by_room = {env.room: env for env in self.envs}

        self.interface.reset()
        self.time = self.interface.tick()

        self.dones = set()
        # while len(self.envs) < self.num_envs:
        #     self.envs.append(self.make_env(len(self.envs)))

        for env in self.envs:
            assert isinstance(env, MultiAgentEnv)

        self.env_states = [_MultiAgentEnvState(env) for env in self.envs]

    @staticmethod
    def get_spaces(agents: List[CreepAgent]):
        return ScreepsMultiAgentEnv.get_spaces(agents)

    def poll(self):
        obs, rewards, dones, infos = {}, {}, {}, {}
        for i, env_state in enumerate(self.env_states):
            obs[i], rewards[i], dones[i], infos[i] = env_state.poll()
        return obs, rewards, dones, infos, {}

    def send_actions(self, action_dict):
        """
        Sends a list of actions to each sub-environment running on the server, then runs the tick and returns data
        from each sub-environment
        :param action_dict: { [environment_id]: { [agent_id]: action } }
        """

        # Pre-tick operations ==============================================

        # Build a dictionary of {username: {creepName: [list of actions and arguments] } }
        all_actions = {}

        # Run all pre-tick actions for each environment
        for env_id, agent_dict in action_dict.items():

            if env_id in self.dones:
                raise ValueError(f"Env {env_id} is already done")

            env = self.envs[env_id]
            env_actions = env.step_pre_tick(agent_dict)

            for username, creep_action_dict in env_actions.items():

                if all_actions.get(username) is None:
                    all_actions[username] = {}
                all_actions[username].update(creep_action_dict)

        # At-tick operations ===============================================

        # Send actions over the interface
        self.interface.send_all_actions(all_actions)

        # Run the tick
        self.time = self.interface.tick()

        # Get all room states and set env.state for each environment
        all_states = self.interface.get_all_room_states()
        for room, state in all_states.items():
            env = self.envs_by_room[room]
            env.state = state

        # Post-tick operations ==============================================

        # Retrieve observations for each environment
        for env_id, agent_dict in action_dict.items():

            env = self.envs[env_id]
            obs, rewards, dones, infos = env.step_post_tick(agent_dict, env.state)

            assert isinstance(obs, dict), "Not a multi-agent obs"
            assert isinstance(rewards, dict), "Not a multi-agent reward"
            assert isinstance(dones, dict), "Not a multi-agent return"
            assert isinstance(infos, dict), "Not a multi-agent info"

            if set(obs.keys()) != set(rewards.keys()):
                raise ValueError(f"Key set for obs and rewards must be the same: {obs.keys()} vs {rewards.keys()}")
            if set(infos).difference(set(obs)):
                raise ValueError(f"Key set for infos must be a subset of obs: {infos.keys()} vs {obs.keys()}")
            if "__all__" not in dones:
                raise ValueError("In multi-agent environments, '__all__': True|False must "
                                 "be included in the 'done' dict: got {}.".format(dones))

            if dones["__all__"]:
                self.dones.add(env_id)

            self.env_states[env_id].observe(obs, rewards, dones, infos)

    def try_reset(self, env_id):
        obs = self.env_states[env_id].reset()
        assert isinstance(obs, dict), "Not a multi-agent obs"
        if obs is not None and env_id in self.dones:
            self.dones.remove(env_id)
        return obs

    def get_unwrapped(self):
        return [state.env for state in self.env_states]
