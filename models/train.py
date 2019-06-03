from socket import gethostname

import ray
from ray import tune
from ray.tune import register_env
from screeps_rl_env import ScreepsEnv, ScreepsVectorEnv

# def train(config, reporter):
#     # Train for 100 iterations with high LR
#     agent1 = PPOTrainer(env="screeps", config=config)
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

    register_env("screeps", lambda config: ScreepsEnv(config))
    register_env("screeps_vectorized", lambda config: ScreepsVectorEnv(config, num_envs = 20))

    LOCAL_HOST_NAME = "tau"
    if gethostname() != LOCAL_HOST_NAME:
        # Running on a cluster
        ray.init(redis_address = "localhost:6379")
        print("---Running on cluster---")
        print("Cluster resources:", ray.cluster_resources())
    else:
        # Running on local machine
        print("Running locally")
        ray.init()

    # ModelCatalog.register_custom_model("my_model", CustomModel)
    tune.run(
            "IMPALA",
            stop = {
                "timesteps_total": 1e4,
            },
            config = {
                "env"        : "screeps_vectorized",  # "screeps",  # or "corridor" if registered above
                "lr"         : 1e-3,  # grid_search([1e-2 , 1e-4, 1e-6]),  # try different lrs
                "num_gpus"   : 0,
                "num_workers": 2,  # parallelism
                # "num_envs_per_worker": 10,
                "env_config" : {
                    "use_backend": False,
                },
            },
    )
