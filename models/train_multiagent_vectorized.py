import argparse

import gym
import ray
from ray import tune
from ray.rllib.agents.ppo import PPOTrainer
from ray.rllib.agents.qmix import QMixTrainer

from screeps_rl_env import ScreepsMultiAgentVectorEnv, CreepAgent
from screeps_rl_env.processors_multiagent import CombatMultiAgentProcessor, ApproachMultiAgentProcessor

parser = argparse.ArgumentParser(description="Train multi-agent model")
parser.add_argument("--model", type=str, default="APEX_QMIX")
parser.add_argument("--cluster", type=bool, default=False)  # not running_on_laptop())
parser.add_argument("--num_workers", type=int, default=2)
parser.add_argument("--num_envs_per_worker", type=int, default=5)
parser.add_argument("--debug", type=bool, default=True)

if __name__ == "__main__":
    args = parser.parse_args()

    if args.cluster:
        ray.init(redis_address="localhost:6379")
    else:
        ray.init()
    print("Cluster resources:", ray.cluster_resources())

    # Generate agents
    num_creeps_per_side = [2, 2]
    creeps_player1 = [CreepAgent(1, i) for i in range(num_creeps_per_side[0])]
    creeps_player2 = [CreepAgent(2, i, is_bot=True) for i in range(num_creeps_per_side[1])]
    agents_all = [*creeps_player1, *creeps_player2]
    agents_controllable = list(filter(lambda creep: not creep.is_bot, agents_all))

    # Generate grouping
    grouping = {
        "Agent1": [creep.agent_id for creep in filter(lambda _creep: not _creep.is_bot, creeps_player1)],
        "Agent2": [creep.agent_id for creep in filter(lambda _creep: not _creep.is_bot, creeps_player2)],
    }
    # Delete empty groups
    empty_groups = [key for key, agents in grouping.items() if len(agents) == 0]
    for group_id in empty_groups:
        del grouping[group_id]

    processor = CombatMultiAgentProcessor
    # processor = ApproachMultiAgentProcessor

    # Generate grouped observation space
    observation_space, action_space = ScreepsMultiAgentVectorEnv.get_spaces(agents_all, processor=processor)
    observation_space_grouped = gym.spaces.Tuple([observation_space] * len(grouping["Agent1"]))
    action_space_grouped = gym.spaces.Tuple([action_space] * len(grouping["Agent1"]))

    # Register environments
    tune.register_env("screeps_multiagent_vectorized",
                      lambda env_config: ScreepsMultiAgentVectorEnv(env_config,
                                                                    processor=processor,
                                                                    num_envs=args.num_envs_per_worker))

    tune.register_env("screeps_multiagent_vectorized_grouped",
                      lambda env_config:
                      ScreepsMultiAgentVectorEnv(env_config,
                                                 processor=processor,
                                                 num_envs=args.num_envs_per_worker)
                      .with_agent_groups(grouping,
                                         obs_space=observation_space_grouped,
                                         act_space=action_space_grouped))

    config = {
        # "lr"         : grid_search([1e-2 , 1e-4, 1e-6]),  # try different lrs
        "num_gpus": 0,
        "num_workers": args.num_workers,  # parallelism
        "num_envs_per_worker": args.num_envs_per_worker,
        "remote_worker_envs": True,
        "env_config": {
            "agents": agents_all,
            "use_backend": False,
        },
    }

    if args.model == "QMIX":
        config = {
            **config,
            "env": "screeps_multiagent_vectorized_grouped",
            "learning_starts": 5000,
            "double_q": False,
        }
    elif args.model == "APEX_QMIX":
        config = {
            **config,
            "env": "screeps_multiagent_vectorized_grouped",
        }
    elif args.model == "PPO":
        policies = {creep.agent_id: (None, observation_space, action_space, {}) for creep in agents_controllable}
        config = {
            **config,
            "env": "screeps_multiagent_vectorized",
            "multiagent": {
                "policies": policies,
                "policy_mapping_fn": tune.function(lambda agent_id: agent_id),
            }
        }

    if args.debug:
        # trainer = QMixTrainer(
        #     env="screeps_multiagent_vectorized_grouped",
        #     config={
        #         "num_workers": 0,
        #         "num_envs_per_worker": args.num_envs_per_worker,
        #         "env_config": {
        #             "agents": agents,
        #             "use_backend": False,
        #         },
        #     }
        # )
        trainer = PPOTrainer(
            env="screeps_multiagent_vectorized",
            config={
                "num_workers": 0,
                "num_envs_per_worker": args.num_envs_per_worker,
                "env_config": {
                    "agents": agents_all,
                    "use_backend": False,
                },
                "multiagent": {
                    "policies": {creep.agent_id: (None, observation_space, action_space, {}) for creep in agents_controllable},
                    "policy_mapping_fn": tune.function(lambda agent_id: agent_id),
                },
            }
        )
        trainer.train()
    else:
        tune.run(
            args.model,
            stop={
                "timesteps_total": 1e9,
            },
            config=config,
            checkpoint_freq=100,
            checkpoint_at_end=True,
            reuse_actors=True,
            queue_trials=True
        )
