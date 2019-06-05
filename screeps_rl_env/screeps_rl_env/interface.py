import json
import os
from subprocess import Popen

import numpy as np
import zerorpc

import atexit

ROOM = "E0S0"  # default room
BACKEND_RELATIVE_PATH = "../../screeps-rl-backend/backend/server.js"
BACKEND_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), BACKEND_RELATIVE_PATH)
RL_ACTION_SEGMENT = 70

def terminate_server_process(proc):
    print("Terminating Screeps server process with pid {}".format(proc.pid))
    proc.terminate()

class ScreepsInterface:
    """
    Represents an interface to communicate with the screeps-rl-backend module, which controls the screeps server
    environment. This can in turn be controlled by the ScreepsEnv gym environment.
    """

    def __init__(self, worker_index, use_backend = False):

        self.index = worker_index
        self.gamePort = 21025 + 5 * worker_index
        self.port = 22025 + 5 * worker_index

        #
        print("Starting remote server at " + str(self.port) + "...")
        self.server_process = Popen(["node", BACKEND_PATH, str(self.index)])
        atexit.register(terminate_server_process, self.server_process)

        self.c = zerorpc.Client(connect_to = "tcp://127.0.0.1:" + str(self.port),
                                timeout = 15,
                                heartbeat = 3,
                                passive_heartbeat = True)

        self.all_rooms = []

        if use_backend:
            self.start_backend()

    def add_env(self, vector_index):
        print("Adding environment with vector_index {}...".format(vector_index))
        room_name = self.c.addEnv(vector_index)
        print("Environment with vector_index {} added to room {}".format(vector_index, room_name))
        self.all_rooms.append(room_name)
        return room_name

    def start_backend(self):
        """Start the backend, necessary if you want to view the world with the Screeps client"""
        print("Starting backend")
        self.c.startBackend()

    def reset(self):
        """Reset the server environment"""
        print("Resetting training environment")
        self.c.resetTrainingEnvironment()

        # Clear caches
        self.terrain_cache = {}

    def reset_room(self, room, creep_config = None):
        del self.terrain_cache[room]
        self.c.resetRoom(room, json.dumps(creep_config))

    def tick(self):
        """Run for a tick"""
        # start = time()
        return self.c.tick()
        # print(f"Time elapsed RPC: {time() - start}")

    def run(self, ticks = 100):
        """Run for many ticks"""
        for tick in range(ticks):
            self.tick()

    def _get_all_room_names(self):
        return self.c.listRoomNames()

    def _get_room_terrian(self, room):
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

    def _get_all_room_terrian(self):
        """
        Get the terrian of all rooms and return as an object
        :param room: the room name to fetch
        :return: np.ndarray the terrain matrix of the room
        """
        all_terrain = {}
        for room in self.all_rooms:
            all_terrain[room] = self._get_room_terrian(room)
        return all_terrain

    def _get_room_objects(self, room = ROOM):
        """
        Get a list of all room objects in the room. Each object is a JSON-style dictionary
        :param room: the room name to fetch
        :return: list of dictionaries representing each room object
        """
        return self.c.getRoomObjects(room)

    def _get_all_room_objects(self):
        """
        Get a list of all room objects in every room. Returns object indexed by room name
        :param room: the room name to fetch
        :return: list of dictionaries representing each room object
        """
        return self.c.getAllRoomObjects()

    def _get_room_event_log(self, room = ROOM):
        """
        Gets the event log for a room, describing the events that happened on previous tick
        :param room: the room name to fetch
        :return: Room.eventLog as a list
        """
        return self.c.getEventLog(room)

    def _get_all_room_event_logs(self):
        """
        Gets the event logs for every room in the simulation, indexed by room name
        :param room: the room name to fetch
        :return: Room.eventLog as a list
        """
        return self.c.getAllEventLogs()

    def get_room_state(self, room):
        """
        Get the full state of the room, returning terrain, room objects, and event log
        :return: dictionary of terrain, roomObjects, eventLog
        """
        return {
            "terrain"    : self._get_room_terrian(room),
            "roomObjects": self._get_room_objects(room),
            "eventLog"   : self._get_room_event_log(room)
        }

    def get_all_room_states(self):
        """
        Get the full state of all rooms room, returning terrain, room objects, and event log
        :return: dictionary of terrain, roomObjects, eventLog
        """
        terrain = self._get_all_room_terrian()
        room_objects = self._get_all_room_objects()
        event_logs = self._get_all_room_event_logs()

        return {
            room: {
                "terrain"    : terrain[room],
                "roomObjects": room_objects[room],
                "eventLog"   : event_logs[room]
            } for room in self.all_rooms
        }

    def send_action(self, actions, username):
        """
        Writes the serialized action to the user memory
        :param actions: a dictionary of {creepName: [list of actions and arguments] }
        """
        actions = json.dumps(actions)
        self.c.sendCommands(username, actions)

    def send_all_actions(self, all_actions):
        """
        Writes the serialized actions to the user memory
        :param all_actions: a dictionary of {username: {creepName: [list of actions and arguments] } }
        """
        for username, user_actions in all_actions.items():
            # self.c.setMemorySegment(username, RL_ACTION_SEGMENT, user_actions)
            self.c.sendCommands(username, json.dumps(user_actions))

    def close(self):
        """Close child processes"""
        print("Stopping")
        self.c.stopServer()

        print("Exiting")
        self.c.exit()

        print("Closing client")
        self.c.close()

        print("Polling")

        print("Response: " + str(self.server_process.poll()))

        self.server_process.terminate()

