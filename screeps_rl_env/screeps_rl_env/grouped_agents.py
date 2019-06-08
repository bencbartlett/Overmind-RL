from collections import OrderedDict
from typing import Dict, List, Any, Callable

import gym
from ray.rllib import BaseEnv
from ray.rllib.env.constants import GROUP_REWARDS, GROUP_INFO

from screeps_rl_env import ScreepsMultiAgentVectorEnv


class GroupedAgentsWrapper(BaseEnv):
    """
    Wraps a BaseEnv environment with agents grouped as specified.
    """

    def __init__(self,
                 env: ScreepsMultiAgentVectorEnv,
                 groups: Dict[str, List[str]],
                 obs_space: gym.spaces.Tuple = None,
                 act_space: gym.spaces.Tuple = None):
        """
        Wrap a ScreepsMultiAgentVectorEnv with agent groupings
        :param env: (ScreepsMultiAgentVectorEnv) the environment to wrap
        :param groups: (dict) example: { "group1": ["agent1", "agent2"], "group2": ["agent3", "agent4"] }
        :param obs_space: optional Tuple observation space
        :param act_space: optional Tuple action space
        """

        self.env = env
        self.groups = groups

        # Generate a mapping of { [agent_id]: group_id }
        self.agent_id_to_group = {}
        for group_id, agent_ids in groups.items():
            for agent_id in agent_ids:
                if agent_id in self.agent_id_to_group:
                    raise ValueError("Agent id {} is in multiple groups".format(agent_id, groups))
                self.agent_id_to_group[agent_id] = group_id

        # Register observation and action space
        if obs_space is not None:
            self.observation_space = obs_space
        if act_space is not None:
            self.action_space = act_space

    def poll(self):
        """
        Returns grouped observations for each environment.
        :return: { [env_id]: (grouped_obs, grouped_rewards, grouped_dones, grouped_infos, off_policy_actions) }, where 
        each item returned is grouped as { [group_id]: [item for each agent in the group] }
        """
        obs_all, rewards_all, dones_all, infos_all, off_policy_actions_all = self.env.poll()

        obs_grouped = {
            env_id: self._group_items(obs, aggregator=lambda group_items: list(group_items.values()))
            for env_id, obs in obs_all.items()
        }
        rewards_grouped = {
            env_id: self._group_items(rewards, aggregator=lambda group_items: list(group_items.values()))
            for env_id, rewards in rewards_all.items()
        }
        dones_grouped = {
            env_id: self._group_items(dones, aggregator=lambda group_items: all(group_items.values()))
            for env_id, dones in dones_all.items()
        }
        infos_grouped = {
            env_id: self._group_items(infos, aggregator=lambda group_items: {GROUP_INFO: list(group_items.values())})
            for env_id, infos in infos_all.items()
        }
        off_policy_actions_grouped = {
            env_id: self._group_items(off_policy_actions, aggregator=lambda group_items: list(group_items.values()))
            for env_id, off_policy_actions in off_policy_actions_all.items()
        }

        # Aggregate rewards, but preserve the original values in infos
        for env_id, env_group_rewards in rewards_grouped.items():
            infos = infos_grouped[env_id]
            for group_id, group_rewards in env_group_rewards.items():
                if isinstance(group_rewards, list):
                    # print("REWARDS: ",group_rewards)
                    if None in group_rewards:
                        env_group_rewards[group_id] = None
                    else:
                        env_group_rewards[group_id] = sum(group_rewards)
                    if group_id not in infos:
                        infos[group_id] = {}
                    infos[group_id][GROUP_REWARDS] = group_rewards

        # Return everything
        return obs_grouped, rewards_grouped, dones_grouped, infos_grouped, off_policy_actions_grouped

    def send_actions(self, action_dict: Dict):
        """
        Receives nested dictionary of grouped actions indexed by environment_id and group_id, ungroups them, and sends
        the ungrouped dictionary of actions indexed by environment_id and agent_id to the internal environment
        :param action_dict: { [environment_id]: { [group_id]: [action for each agent in the group] } }
        """

        # Ungroup actions for each environment
        action_dict_ungrouped = {}
        for env_id, grouped_actions in action_dict.items():
            action_dict_ungrouped[env_id] = self._ungroup_items(grouped_actions)

        self.env.send_actions(action_dict_ungrouped)

    def try_reset(self, env_id):
        obs = self.env.try_reset(env_id)
        return self._group_items(obs, aggregator=lambda group_items: list(group_items.values()))

    def get_unwrapped(self):
        return [state.env for state in self.env.env_states]

    # def reset(self):
    #     obs = self.env.reset()
    #     return self._group_items(obs)
    #
    # def step(self, action_dict):
    #     # Ungroup and send actions
    #     ungrouped_action_dict = self._ungroup_items(action_dict)
    #     obs, rewards, dones, infos = self.env.step(ungrouped_action_dict)
    #
    #     # Apply grouping transforms to the env outputs
    #     obs = self._group_items(obs, aggregator=lambda group_items: list(group_items.values()))
    #     rewards = self._group_items(rewards, aggregator=lambda group_items: list(group_items.values()))
    #     dones = self._group_items(dones, aggregator=lambda group_items: all(group_items.values()))
    #     infos = self._group_items(infos, aggregator=lambda group_items: {GROUP_INFO: list(group_items.values())})
    #
    #     # Aggregate rewards, but preserve the original values in infos
    #     for agent_id, reward in rewards.items():
    #         if isinstance(reward, list):
    #             rewards[agent_id] = sum(reward)
    #             if agent_id not in infos:
    #                 infos[agent_id] = {}
    #             infos[agent_id][GROUP_REWARDS] = reward
    #
    #     return obs, rewards, dones, infos

    def _ungroup_items(self, action_dict: Dict[str, Any]):
        """
        Un-group actions which have been grouped as in self._group_items()
        :param action_dict: a dict of { [group_id]: [action for each agent in the group] }
        :return:
        """
        ungrouped_actions = {}
        for group_id, actions in action_dict.items():
            # If the id corresponds to a group, iterate through each agent in the group and assign respective actions
            if group_id in self.groups:
                assert len(actions) == len(self.groups[group_id]), (group_id, actions, self.groups)
                for agent, action in zip(self.groups[group_id], actions):
                    ungrouped_actions[agent] = action

            # If the id is not a group, it must be an agent id
            else:
                ungrouped_actions[group_id] = actions

        return ungrouped_actions

    def _group_items(self, items: Dict[str, Any], aggregator: Callable[[OrderedDict], Any] = None) -> Dict:
        """
        Generate a grouping of return items indexed by group_id
        :param items: a MultiAgentEnv-style dictionary of { [agent_id]: ob/reward/done/info }
        :param aggregator: a function to convert agent items to group items
        :return: a dict of { [group_id]: [item for each agent in the group] }
        """
        grouped_items = {}
        for agent_id, item in items.items():
            if agent_id in self.agent_id_to_group:
                # Index grouped_items by group_id
                group_id = self.agent_id_to_group[agent_id]
                if group_id in grouped_items:
                    continue  # already added

                # The first time you encounter a new group, create a dict of items for all agents in that group
                group_out = OrderedDict()
                for agent_of_group in self.groups[group_id]:
                    if agent_of_group in items:
                        group_out[agent_of_group] = items[agent_of_group]
                    else:
                        raise ValueError(f"Missing member of group {group_id}: {agent_of_group}: {items}")

                # Assign the group outputs to the group-indexed items
                grouped_items[group_id] = aggregator(group_out)
            else:
                # Agents not in a group are simply indexed by their id
                grouped_items[agent_id] = item

        return grouped_items

    def close(self):
        self.env.close()
