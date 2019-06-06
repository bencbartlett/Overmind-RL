import time

import ray
from ray.rllib import PolicyEvaluator
from ray.rllib.optimizers import SyncReplayOptimizer
from ray.rllib.optimizers.replay_buffer import ReplayBuffer


class AlphaGoZero:

    def __init__(self):
        self.best_model = AlphaGoEvaluator()
        self.replay_buffer = SharedReplayBuffer.remote()

        # optimizers pull from the shared replay buffer to improve their model
        self.optimizers = [AlphaGoOptimizer.remote(self.replay_buffer) for _ in range(20)]
        self.optimizer_tasks = []
        weights = self.best_model.get_weights()

        for opt in self.optimizers:
            opt.set_weights.remote(weights)
            self.optimizer_tasks.append(opt.step.remote())

        # self-play evaluators constantly evaluate the current best model and add samples into shared replay buffer
        self.self_play_evaluators = [AlphaGoEvaluator.remote() for _ in range(20)]
        self.self_play_tasks = []
        for ev in self.self_play_evaluators:
            self.self_play_tasks.append(ev.sample.remote())

        # when optimizers finish an optimization round, their model is compared with current best to see if it can replace
        self.compare_tasks = []

    def train(self):
        result = elo_estimate.remote(self.best_model)
        start = time.time()

        while time.time() - start < 60 or not ray.wait(result, timeout = 0.0):
            self._step()

        return result

    def _step(self):
        result_id, result_worker, _ = ray.wait(self.optimizer_tasks + self.self_play_tasks + self.compare_tasks)

        if result_id in self.optimizer_tasks:
            # launch a compare task to see if we can beat the best model
            self.compare_tasks.append(compare_models.remote(self.best_model, result_id))
            # continue optimization on this worker
            self.self_play_tasks.append(result_worker.sample.remote())
            self.self_play_tasks.remove(result_id)

        if result_id in self.compare_tasks:
            self.compare_tasks.remove(result_id)
            result = ray.get(result_id)

            # if it beats the current best model, broadcasat new weights to all evaluators and optimizers
            if result.win_ratio >= 0.55:
                self.best_model = ray.get(result.model)
                weights = ray.put(self.best_model.get_weights())

                for ev in self.self_play_evaluators:
                    ev.set_weights.remote(weights)
                for opt in self.optimizers:
                    opt.set_weights.remote(weights)
                ray.kill(self.compare_tasks)
                self.compare_tasks = []


@ray.remote
class AlphaGoEvaluator(PolicyEvaluator):
    def sample(self):
        return None  # self-play rolouts based on current policy


@ray.remote
class AlphaGoOptimizer(SyncReplayOptimizer):
    def __init__(self, replay_buffer):
        self.evaluator = AlphaGoEvaluator()
        SyncReplayOptimizer.__init__(self.evaluator, [replay_buffer])

    def set_weights(self, weights):
        self.evaluator.set_weights(weights)


@ray.remote
class SharedReplayBuffer(ReplayBuffer):
    pass


@ray.remote
def compare_models(current_best, candidate):
    # compares the models, returning the candidate win ratio
    pass


@ray.remote
def elo_estimate(model):
    # returns an ELO estimate of the given model
    pass
