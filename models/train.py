from socket import gethostname

import argparse

import ray
from ray import tune
from ray.rllib.agents.impala import ImpalaTrainer
from ray.rllib.agents.ppo import PPOTrainer
from ray.tune import register_env, grid_search
from screeps_rl_env import ScreepsEnv, ScreepsVectorEnv

# def train(config, reporter):
#     # Train for 100 iterations with high LR
#     agent1 = ImpalaTrainer(env="screeps_vectorized", config=config)
#     for _ in range(10):
#         result = agent1.train()
#         result["phase"] = 1
#         reporter(**result)
#         phase1_time = result["timesteps_total"]
#     state = agent1.save()
#     agent1.stop()
#
#     # Train for 100 iterations with low LR
#     config["lr"] = 0.0001
#     agent2 = PPOTrainer(env="CartPole-v0", config=config)
#     agent2.restore(state)
#     for _ in range(10):
#         result = agent2.train()
#         result["phase"] = 2
#         result["timesteps_total"] += phase1_time  # keep time moving forward
#         reporter(**result)
#     agent2.stop()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description = "Train a model with many workers")
    parser.add_argument("--num_machines", type = int, default = 1)
    # parser.add_argument("--num_workers", type = int, default = None)

    args = parser.parse_args()

    register_env("screeps", lambda config: ScreepsEnv(config))
    register_env("screeps_vectorized", lambda config: ScreepsVectorEnv(config, num_envs = 20))

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

    # ModelCatalog.register_custom_model("my_model", CustomModel)
    tune.run(
            "PPO",
            stop = {
                "timesteps_total": 1e6,
            },
            config = {
                "env"        : "screeps_vectorized",  # "screeps",  # or "corridor" if registered above
                # "lr"         : grid_search([1e-2 , 1e-4, 1e-6]),  # try different lrs
                "num_gpus"   : 0,
                "num_workers": 6,  # parallelism
                # "num_envs_per_worker": 10,
                "env_config" : {
                    "use_backend": False,
                },
            },
            checkpoint_freq = 100000,
            checkpoint_at_end = True,
            queue_trials = True
    )
