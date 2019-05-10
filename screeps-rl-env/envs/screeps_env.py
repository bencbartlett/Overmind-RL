from subprocess import Popen
from time import time

import gym
import zerorpc

PATH_TO_BACKEND = "../../screeps-rl-backend/backend/server.js"


class ScreepsEnv(gym.Env):

    def __init__(self, index = 0, use_backend = False):
        self.index = index
        self.gamePort = 21025 + 5 * index
        self.port = 22025 + 5 * index

        self._start_server_process()
        if use_backend:
            self._start_backend()

    def _start_server_process(self):
        print("Starting remote server at " + str(self.gamePort) + "...")
        self.server_process = Popen(["node", PATH_TO_BACKEND, str(self.index)])

        self.c = zerorpc.Client()
        self.c.connect("tcp://127.0.0.1:" + str(self.port))
        print("Connected")

    def _start_server(self):
        '''Start the server'''
        print("Starting processor")
        self.c.startServer()

    def _start_backend(self):
        '''Start the backend, necessary if you want to view the world with the Screeps client'''
        print("Starting backend")
        self.c.startBackend()

    def tick(self):
        '''Run for a tick'''
        start = time()
        self.c.tick()
        print(f"Time elapsed RPC: {time() - start}")

    def run(self, ticks = 100):
        '''Run for many ticks'''
        for tick in range(ticks):
            self.tick()

    # gym.Env methods ==================================================================================================

    def step(self, action):
        pass

    def reset(self):
        '''Reset the server environment'''
        print("Resetting training environment")
        self.c.resetTrainingEnvironment()
        self._start_server()

    def render(self, mode = 'human'):
        pass

    def seed(self, seed = None):
        pass

    def close(self):
        '''Close child processes'''
        print("Stopping")
        self.c.stopServer()

        print("Exiting")
        self.c.exit()

        print("Polling")

        print("Response: " + str(self.server_process.poll()))

        self.server_process.kill()


if __name__ == "__main__":
    env = ScreepsEnv(1)
    env.reset()
    env.run(100)
    env.close()
