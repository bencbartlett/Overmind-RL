import zerorpc
from multiprocessing import Pool
from subprocess import call, Popen
from time import time

class ScreepsEnvironment:

    def __init__(self, index):
        self.index = index
        self.port = index + 22025

        print("Starting remote server at " + str(self.port) + "...")
        self.serverprocess = Popen(["node", "../remoteServer/server.js", str(self.index)])


        self.c = zerorpc.Client()
        self.c.connect("tcp://127.0.0.1:"+str(self.port))
        print("Connected")

    def run(self):
        print(f"Test1: {self.c.test()}")
        print(f"Test2: {self.c.test()}")
        print(f"Test3: {self.c.test()}")

        print("Initializing")
        self.c.initializeServer()

        print("Starting")
        self.c.startServer()

        for tick in range(100):
            print("Running tick "+str(tick))
            start = time()
            tick = self.c.tick()
            print(f"Time elapsed RPC: {time() - start}")
            print("Reply: "+str(tick))

        print("Stopping")
        self.c.stopServer()

        print("Exiting")
        self.c.exit()

        print("Polling")

        print("Response: "+str(self.serverprocess.poll()))

        self.serverprocess.kill()

        

if __name__ == "__main__":
    env = ScreepsEnvironment(14)
    env.run()