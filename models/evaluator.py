from ray.rllib import PolicyEvaluator
from screeps_rl_env import ScreepsInterface


class ScreepsEvaluator(PolicyEvaluator):
    """
    Customized PolicyEvaluator which contains a local ScreepsInterface object shared among all environment instances.
    """

    def __init__(self, *args, **kwargs):
        worker_index = kwargs['worker_index'] if 'worker_index' in kwargs else 0
        env_config = kwargs['env_config'] if 'env_config' in kwargs else {}

        # Create an interface object shared among the evaluator
        num_envs = kwargs['num_envs'] if 'num_envs' in kwargs else 1
        auto_vectorize = num_envs > 1
        self.interface = ScreepsInterface(worker_index, auto_vectorize = auto_vectorize)

        # Put interface and auto-vectorize toggle in the environment configuration dict
        env_config['interface'] = self.interface
        env_config['auto_vectorize'] = auto_vectorize

        super().__init__(*args, **kwargs)
