import argparse

import gym
import ray
from ray import tune
from ray.rllib.agents.qmix import QMixTrainer

from screeps_rl_env import ScreepsMultiAgentVectorEnv, CreepAgent

# def training_workflow(config, reporter):
#
#     # Setup policy and policy evaluation actors
#
#     with tf.Session() as sess:
#         workers = [
#             PolicyEvaluator.as_remote().remote(
#                     lambda config: ScreepsMultiAgentEnv(config, worker_index = i, num_envs = 10),
#                     # lambda config: ScreepsEnv(config, worker_index = i, vector_index = 0),
#                     # lambda c: gym.make("CartPole-v0"),
#                     PPOTFPolicy)
#             for i in range(config["num_workers"])
#         ]
#
#         # TODO: hardcoded spaces
#         observation_space = gym.spaces.MultiDiscrete([50, 50, 50, 50])
#         action_space = gym.spaces.Discrete(8)
#
#         policy = PPOTFPolicy(observation_space, action_space, {})
#
#         for _ in range(config["num_iters"]):
#             # Broadcast weights to the policy evaluation workers
#             weights = ray.put({"default_policy": policy.get_weights()})
#             for w in workers:
#                 w.set_weights.remote(weights)
#
#             # Gather a batch of samples
#             batch = SampleBatch.concat_samples(ray.get([w.sample.remote() for w in workers]))
#
#             # Improve the policy using the batch
#             policy.learn_on_batch(batch)
#
#             reporter(**collect_metrics(remote_evaluators = workers))


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Train multi-agent model")
    parser.add_argument("--cluster", type=bool, default=False)
    parser.add_argument("--num_workers", type=int, default=6)
    parser.add_argument("--num_envs_per_worker", type=int, default=10)
    parser.add_argument("--grouped", type=bool, default=True)

    args = parser.parse_args()

    if args.cluster:
        # Running on a cluster
        ray.init(redis_address="localhost:6379")
        print("---Running on cluster---")
    else:
        # Running on local machine
        print("---Running locally---")
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

    # Generate grouped observation space
    observation_space, action_space = ScreepsMultiAgentVectorEnv.get_spaces(agents)
    observation_space_grouped = gym.spaces.Tuple([observation_space] * len(grouping["Agent1"]))
    action_space_grouped = gym.spaces.Tuple([action_space] * len(grouping["Agent1"]))

    tune.register_env("screeps_multiagent_vectorized",
                      lambda config:
                      ScreepsMultiAgentVectorEnv(config, num_envs=args.num_envs_per_worker).with_agent_groups(
                          grouping, obs_space=observation_space_grouped, act_space=action_space_grouped
                      ))

    # policies = {
    #     creep.agent_id: (None, observation_space, action_space, {}) for creep in agents
    # }

    # trainer = QMixTrainer(
    #     env="screeps_multiagent_vectorized",
    #     config={
    #         "num_workers": 0,  # args.num_workers,  # parallelism
    #         "num_envs_per_worker": args.num_envs_per_worker,
    #         # "remote_worker_envs": True,
    #         "env_config": {
    #             "agents": agents,
    #             "use_backend": False,
    #         },
    #     }
    # )
    #
    # trainer.train()

    tune.run(
        "QMIX",
        stop={
            "timesteps_total": 5e5,
        },
        config={
            "env": "screeps_multiagent_vectorized",
            # "lr"         : grid_search([1e-2 , 1e-4, 1e-6]),  # try different lrs
            "num_gpus": 0,
            "num_workers": 0,#args.num_workers,  # parallelism
            "num_envs_per_worker": args.num_envs_per_worker,
            # "remote_worker_envs": True,
            "env_config": {
                "agents": agents,
                "use_backend": False,
            },
            # "multiagent": {
            #     "policies": policies,
            #     "policy_mapping_fn": tune.function(lambda agent_id: agent_id),
            # }
        },
        checkpoint_freq=100,
        checkpoint_at_end=True,
        queue_trials=True
    )
