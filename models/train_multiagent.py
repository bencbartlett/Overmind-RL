import argparse

import argparse

import ray
from ray import tune
from ray.tune import register_env
from screeps_rl_env import ScreepsMultiAgentEnv, CreepAgent

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description = "Train a model with many workers")
    parser.add_argument("--num_machines", type = int, default = 1)
    # parser.add_argument("--num_workers", type = int, default = None)

    args = parser.parse_args()

    LOCAL_HOST_NAME = "tau"

    if args.num_machines > 1:
        # Running on a cluster
        ray.init(redis_address = "localhost:6379")
        print("---Running on cluster---")
    else:
        # Running on local machine
        print("---Running locally---")
        ray.init()

    print("Cluster resources:", ray.cluster_resources())

    num_creeps_per_side = [2, 2]
    creeps_player1 = [CreepAgent(1, i) for i in range(num_creeps_per_side[0])]
    creeps_player2 = [CreepAgent(2, i) for i in range(num_creeps_per_side[1])]
    agents = [*creeps_player1, *creeps_player2]

    register_env("screeps_multiagent", lambda config: ScreepsMultiAgentEnv(config, agents = agents))

    observation_space, action_space = ScreepsMultiAgentEnv.get_spaces(agents)
    policies = {
        creep.agent_id: (None, observation_space, action_space, {}) for creep in agents
    }

    tune.run(
            "PPO",
            stop = {
                "timesteps_total": 5e5,
            },
            config = {
                "env"        : "screeps_multiagent",
                # "lr"         : grid_search([1e-2 , 1e-4, 1e-6]),  # try different lrs
                "num_gpus"   : 0,
                "num_workers": 0,  # parallelism
                "num_envs_per_worker": 10,
                # "remote_worker_envs": True,
                "env_config" : {
                    "use_backend": False,
                },
                "multiagent" : {
                    "policies": policies,
                    "policy_mapping_fn": tune.function(lambda agent_id: agent_id),
                }
            },
            checkpoint_freq = 100,
            checkpoint_at_end = True,
            queue_trials = True
    )
