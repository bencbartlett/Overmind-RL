import argparse

import gym
import ray
from ray import tune

from screeps_rl_env import ScreepsMultiAgentVectorEnv, CreepAgent
from screeps_rl_env.processors_multiagent import CombatMultiAgentProcessor

parser = argparse.ArgumentParser(description="Train multi-agent model")
parser.add_argument("--model", type=str, default="APEX_QMIX")
parser.add_argument("--cluster", type=bool, default=False)  # not running_on_laptop())
parser.add_argument("--num_workers", type=int, default=2)
parser.add_argument("--num_envs_per_worker", type=int, default=5)

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
    creeps_player2 = [CreepAgent(2, i) for i in range(num_creeps_per_side[1])]
    agents = [*creeps_player1, *creeps_player2]

    # Generate grouping
    grouping = {
        "Agent1": [creep.agent_id for creep in creeps_player1],
        "Agent2": [creep.agent_id for creep in creeps_player2],
    }

    processor = CombatMultiAgentProcessor

    # Generate grouped observation space
    observation_space, action_space = ScreepsMultiAgentVectorEnv.get_spaces(agents, processor=processor)
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
            "agents": agents,
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
        policies = {
            creep.agent_id: (None, observation_space, action_space, {}) for creep in agents
        }
        config = {
            **config,
            "env": "screeps_multiagent_vectorized",
            "multiagent": {
                "policies": policies,
                "policy_mapping_fn": tune.function(lambda agent_id: agent_id),
            }
        }

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
