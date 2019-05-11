import json
from subprocess import Popen
from time import time

import numpy as np
import zerorpc

ROOM = "W0N1"  # default room
PATH_TO_BACKEND = "../../screeps-rl-backend/backend/server.js"
RL_ACTION_SEGMENT = 70


class ScreepsInterface:
    """
    Represents an interface to communicate with the screeps-rl-backend module, which controls the screeps server
    environment. This can in turn be controlled by the ScreepsEnv gym environment.
    """

    def __init__(self, index = 0, use_backend = False):

        self.index = index
        self.gamePort = 21025 + 5 * index
        self.port = 22025 + 5 * index

        self._start_server()
        if use_backend:
            self._start_backend()

        self.terrain_cache = {}

    def _start_server(self):

        print("Starting remote server at " + str(self.gamePort) + "...")
        self.server_process = Popen(["node", PATH_TO_BACKEND, str(self.index)])

        self.c = zerorpc.Client()
        self.c.connect("tcp://127.0.0.1:" + str(self.port))
        print("Connected")

        # print("Starting processor")
        # self.c.startServer()

    # def _start_processor(self):
    #     """Start the server procesor"""
    #     print("Starting processor")
    #     self.c.startServer()

    def _start_backend(self):
        """Start the backend, necessary if you want to view the world with the Screeps client"""
        print("Starting backend")
        self.c.startBackend()

    def reset(self):
        """Reset the server environment"""
        print("Resetting training environment")
        self.c.resetTrainingEnvironment()

        # Clear caches
        self.terrain_cache = {}

        # self._start_processor()

    def tick(self):
        """Run for a tick"""
        start = time()
        self.c.tick()
        print(f"Time elapsed RPC: {time() - start}")

    def run(self, ticks = 100):
        """Run for many ticks"""
        for tick in range(ticks):
            self.tick()

    def _get_room_terrian(self, room = ROOM):
        """
        Get the terrian of the room and return as a 50x50 numpy array
        :param room: the room name to fetch
        :return: np.ndarray the terrain matrix of the room
        """
        cached = self.terrain_cache.get(room)
        if cached is not None:
            return cached
        else:
            terrain_string = self.c.getRoomTerrain(room)
            terrain = np.reshape(np.array(list(terrain_string), dtype = np.uint8), (50, 50))
            self.terrain_cache[room] = terrain
            return terrain

    def _get_room_objects(self, room = ROOM):
        """
        Get a list of all room objects in the room. Each object is a JSON-style dictionary
        :param room: the room name to fetch
        :return: list of dictionaries representing each room object
        """
        return self.c.getRoomObjects(room)

    def _get_room_event_log(self, room = ROOM):
        """
        Gets the event log for a room, describing the events that happened on previous tick
        :param room: the room name to fetch
        :return: Room.eventLog as a list
        """
        return self.c.getEventLog(room)

    def get_room_state(self, room = ROOM):
        """
        Get the full state of the room, returning terrain, room objects, and event log
        :return: dictionary of terrain, roomObjects, eventLog
        """
        return {
            "terrain"    : self._get_room_terrian(room),
            "roomObjects": self._get_room_objects(room),
            "eventLog"   : self._get_room_event_log(room)
        }

    def send_all_actions(self, actions):
        """
        Writes the serialized actions to the user memory
        :param actions: a dictionary of {username: {creepName: [list of actions and arguments] } }
        """
        for username, user_actions in actions.items():
            # self.c.setMemorySegment(username, RL_ACTION_SEGMENT, user_actions)
            self.c.setMemory(username, user_actions)

    def send_action(self, action, username):
        """
        Writes the serialized action to the user memory
        :param action: a dictionary of {creepName: [list of actions and arguments] }
        """
        self.c.setMemory(username, action)

    def close(self):
        """Close child processes"""
        print("Stopping")
        self.c.stopServer()

        print("Exiting")
        self.c.exit()

        print("Polling")

        print("Response: " + str(self.server_process.poll()))

        self.server_process.kill()


if __name__ == "__main__":
    env = ScreepsInterface(0)
    env.reset()
    for tick in range(20):
        actions = {"Agent1": json.dumps({"a1c1": [["move", tick % 8 + 1]]}),
                   "Agent2": json.dumps({"a2c1": [["move", tick % 8 + 1]]})}
        env.send_all_actions(actions)
        ret = env.tick()
        print(f"Response: {ret}")
    # env.run(100)
    env.close()
