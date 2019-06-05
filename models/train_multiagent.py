from socket import gethostname

import argparse

import ray
from ray import tune
from ray.rllib.agents.impala import ImpalaTrainer
from ray.rllib.agents.ppo import PPOTrainer
from ray.tune import register_env, grid_search
from screeps_rl_env import ScreepsEnv, ScreepsMultiAgentEnv

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description = "Train a model with many workers")
    parser.add_argument("--num_machines", type = int, default = 1)
    # parser.add_argument("--num_workers", type = int, default = None)

    args = parser.parse_args()

    register_env("screeps_multiagent", lambda config: ScreepsMultiAgentEnv(config))

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

    # policies

    # ModelCatalog.register_custom_model("my_model", CustomModel)
    tune.run(
            "PPO",
            stop = {
                "timesteps_total": 5e5,
            },
            config = {
                "env"        : "screeps_multiagent",
                # "lr"         : grid_search([1e-2 , 1e-4, 1e-6]),  # try different lrs
                "num_gpus"   : 0,
                "num_workers": 6,  # parallelism
                # "num_envs_per_worker": 10,
                "env_config" : {
                    "use_backend": False,
                },
                "multiagent": {

                }
            },
            checkpoint_freq = 100,
            checkpoint_at_end = True,
            queue_trials = True
    )
