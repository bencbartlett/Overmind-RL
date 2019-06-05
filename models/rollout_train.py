import argparse

import gym
import tensorflow as tf
import ray
from ray import tune
from ray.rllib.agents.ppo.ppo_policy import PPOTFPolicy
from ray.rllib.evaluation import PolicyEvaluator, SampleBatch
from ray.rllib.evaluation.metrics import collect_metrics
from screeps_rl_env import ScreepsVectorEnv, ScreepsEnv

parser = argparse.ArgumentParser()
parser.add_argument("--gpu", action = "store_true")
parser.add_argument("--num-iters", type = int, default = 100)
parser.add_argument("--num-workers", type = int, default = 2)


def training_workflow(config, reporter):

    # Setup policy and policy evaluation actors

    with tf.Session() as sess:
        workers = [
            PolicyEvaluator.as_remote().remote(
                    lambda config: ScreepsVectorEnv(config, worker_index = i, num_envs = 10),
                    # lambda config: ScreepsEnv(config, worker_index = i, vector_index = 0),
                    # lambda c: gym.make("CartPole-v0"),
                    PPOTFPolicy)
            for i in range(config["num_workers"])
        ]

        # TODO: hardcoded spaces
        observation_space = gym.spaces.MultiDiscrete([50, 50, 50, 50])
        action_space = gym.spaces.Discrete(8)

        policy = PPOTFPolicy(observation_space, action_space, {})

        for _ in range(config["num_iters"]):
            # Broadcast weights to the policy evaluation workers
            weights = ray.put({"default_policy": policy.get_weights()})
            for w in workers:
                w.set_weights.remote(weights)

            # Gather a batch of samples
            batch = SampleBatch.concat_samples(ray.get([w.sample.remote() for w in workers]))

            # Improve the policy using the batch
            policy.learn_on_batch(batch)

            reporter(**collect_metrics(remote_evaluators = workers))


if __name__ == "__main__":


    # tune.register_env("screeps_vectorized", lambda config: ScreepsVectorEnv(config, num_envs = 10))

    args = parser.parse_args()
    ray.init()

    tune.run(
            training_workflow,
            resources_per_trial = {
                "gpu"      : 1 if args.gpu else 0,
                "cpu"      : 1,
                "extra_cpu": args.num_workers,
            },
            config = {
                "num_workers": args.num_workers,
                "num_iters"  : args.num_iters,
            },
    )
