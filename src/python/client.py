import zerorpc
from multiprocessing import Pool
from subprocess import call, Popen
from time import time

class ScreepsEnvironment:

    def __init__(self, index):
        self.index = index
        self.gamePort = 21025 + 5 * index
        self.port = 22025 + 5 * index

        print("Starting remote server at " + str(self.gamePort) + "...")
        self.serverprocess = Popen(["node", "../remoteServer/server.js", str(self.index)])


        self.c = zerorpc.Client()
        self.c.connect("tcp://127.0.0.1:"+str(self.port))
        print("Connected")

    def reset(self):
        '''Reset the server environment'''
        print("Resetting training environment")
        self.c.resetTrainingEnvironment()

    def start_server(self):
        '''Start the server'''
        print("Starting processor")
        self.c.startServer()

    def start_backend(self):
        '''Start the backend, necessary if you want to view the world with the Screeps client'''
        print("Starting backend")
        self.c.startBackend()

    def tick(self):
        '''Run for a tick'''
        start = time()
        tick = self.c.tick()
        print(f"Time elapsed RPC: {time() - start}")
        print("Reply: "+str(tick))

    def run(self, ticks=100):
        '''Run for many ticks'''
        for tick in range(ticks):
            self.tick()

    def close(self):
        '''Close child processes'''
        print("Stopping")
        self.c.stopServer()

        print("Exiting")
        self.c.exit()

        print("Polling")

        print("Response: "+str(self.serverprocess.poll()))

        self.serverprocess.kill()

        

if __name__ == "__main__":
    env = ScreepsEnvironment(0)
    env.reset()
    env.start_server()
    env.run(100)
    env.close()
