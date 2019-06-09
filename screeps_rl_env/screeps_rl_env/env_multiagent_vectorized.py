import time
from typing import Dict, Union, List, Type

from ray.rllib import BaseEnv, MultiAgentEnv
from ray.rllib.env import EnvContext
from ray.rllib.env.base_env import _MultiAgentEnvState

from screeps_rl_env import ScreepsMultiAgentEnv, ScreepsInterface, CreepAgent, ScreepsMultiAgentProcessor, \
    ApproachMultiAgentProcessor
from screeps_rl_env.utils import kill_backend_processes

LOG_TICK_RATE_FREQ = 100
KILL_BACKEND_PROCESSES = True


class ScreepsMultiAgentVectorEnv(BaseEnv):

    def __init__(self,
                 env_config: Union[EnvContext, Dict],
                 num_envs: int = 1,
                 processor: Type[ScreepsMultiAgentProcessor] = ApproachMultiAgentProcessor,
                 interface: ScreepsInterface = None,
                 use_backend: bool = False,
                 use_viewer: bool = False):

        if isinstance(env_config, EnvContext):
            self.worker_index = env_config.worker_index
        else:
            self.worker_index = env_config['worker_index'] if 'worker_index' in env_config else 0

        # Backend initialization, usually ignored
        self.use_backend = use_backend

        # Viewer is used for render(mode='rgb_array')
        self.use_viewer = use_viewer

        if interface is None:
            if KILL_BACKEND_PROCESSES:
                kill_backend_processes(self.worker_index)
            time.sleep(3)  # if env was just terminated in a failed actor, wait for interface proc to terminate first
            print(f"==> Starting new ScreepsInterface with worker_index={self.worker_index} <==")
            self.interface = ScreepsInterface(self.worker_index)
            time.sleep(3)  # wait for server to register
        else:
            print('Using existing interface {} with worker index {}'.format(self.interface, self.worker_index))
            self.interface = interface

        # Instantiate environments
        self.num_envs = num_envs
        self.envs = [
            ScreepsMultiAgentEnv(env_config,
                                 processor=processor,
                                 worker_index=self.worker_index,
                                 vector_index=i,
                                 interface=self.interface,
                                 use_backend=self.use_backend,
                                 use_viewer=self.use_viewer)
            for i in range(self.num_envs)
        ]
        self.envs_by_room = {env.room: env for env in self.envs}

        # Perform a hard reset and allow two ticks for scripts to initialize
        self.tick_interval_start = None
        self.interface.reset()
        for _ in range(2):
            # self.time = self.interface.tick()
            self._tick()

        self.dones = set()

        for env in self.envs:
            assert isinstance(env, MultiAgentEnv)

        self.env_states = [_MultiAgentEnvState(env) for env in self.envs]

    @staticmethod
    def get_spaces(agents: List[CreepAgent],
                   processor: Type[ScreepsMultiAgentProcessor] = ApproachMultiAgentProcessor):
        return ScreepsMultiAgentEnv.get_spaces(agents, processor)

    def poll(self):
        """
        Returns observations from ready agents, indexed by env_id then agent_id.
        The number of agents and envs can vary over time.
        :return: nested dict of (obs, rewards, dones, infos, off_policy_actions) indexed by env_id then agent id
            obs: New observations for each ready agent.
            rewards: Reward values for each ready agent. If the episode is just started, the value will be None.
            dones: Done values for each ready agent. The special key "__all__" is used to indicate env termination.
            infos: Info values for each ready agent.
            off_policy_actions: Agents may take off-policy actions. When that happens, there will be an entry in
                this dict that contains the taken action. There is no need to send_actions() for agents that have
                already chosen off-policy actions.
        """
        obs, rewards, dones, infos = {}, {}, {}, {}
        for i, env_state in enumerate(self.env_states):
            obs[i], rewards[i], dones[i], infos[i] = env_state.poll()

        off_policy_actions = {}
        return obs, rewards, dones, infos, off_policy_actions

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
        # self.time = self.interface.tick()
        self._tick()

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

    def _tick(self):
        self.time = self.interface.tick()
        if self.time % LOG_TICK_RATE_FREQ == 2:
            if self.tick_interval_start is not None:
                time_elapsed = time.time() - self.tick_interval_start
                ticks_elapsed = LOG_TICK_RATE_FREQ * self.num_envs
                throughput = ticks_elapsed / time_elapsed
                print(f"Vectorized worker_index={self.worker_index}, tick={self.time}: " +
                      "throughput = {:.2f} tick*room/s".format(throughput))
            self.tick_interval_start = time.time()

    def try_reset(self, env_id):
        obs = self.env_states[env_id].reset()
        assert isinstance(obs, dict), "Not a multi-agent obs"
        if obs is not None and env_id in self.dones:
            self.dones.remove(env_id)
        return obs

    def get_unwrapped(self):
        return [state.env for state in self.env_states]

    def close(self):
        for env in self.envs:
            env.close()

        self.interface.close()

    def with_agent_groups(self, groups, obs_space=None, act_space=None):
        from screeps_rl_env.grouped_agents import GroupedAgentsWrapper
        return GroupedAgentsWrapper(self, groups, obs_space, act_space)
