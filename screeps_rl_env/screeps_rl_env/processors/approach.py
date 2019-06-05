import numpy as np
from screeps_rl_env.processors import ScreepsProcessor


class ApproachProcessor(ScreepsProcessor):
    """
    Train a creep to approach the other creep in the room using base movement intents
    """

    def process_state(self, room_state):
        terrain = room_state["terrain"]
        room_objects = room_state["roomObjects"]
        event_log = room_state["eventLog"]

        my_creep_name = "Agent1_{}:{}".format(0, self.env.room)
        enemy_creep_name = "Agent2_{}:{}".format(0, self.env.room)

        enemy_creeps = list(filter(lambda obj: obj["type"] == "creep" and
                                               obj["name"] == enemy_creep_name, room_objects))
        enemy_creep = enemy_creeps[0] if len(enemy_creeps) > 0 else None

        my_creeps = list(filter(lambda obj: obj["type"] == "creep" and
                                            obj["name"] == my_creep_name, room_objects))
        my_creep = my_creeps[0] if len(my_creeps) > 0 else None

        if enemy_creep is not None and my_creep is not None:
            return np.array([my_creep["x"], my_creep["y"], enemy_creep["x"], enemy_creep["y"]])
        else:
            return None  # TODO: placeholder

    def process_action(self, action, creep_id = 0):
        creep_name = "Agent1_{}:{}".format(creep_id, self.env.room)
        return {creep_name: [["move", int(action) + 1]]}

    def process_reward(self, observation):
        my_x, my_y, foe_x, foe_y = observation
        return 1 / 50 * (50 - np.sqrt((foe_x - my_x) ** 2 + (foe_y - my_y) ** 2))

    def process_observation(self, state):
        """Returns the observation from a room given the state after running self.interface.tick()"""
        ob = self.process_state(state)

        if ob is not None:
            return ob, self.process_reward(ob), False, {}
        else:
            ob = np.array([25, 25, 25, 25])
            return ob, 0, True, {}
