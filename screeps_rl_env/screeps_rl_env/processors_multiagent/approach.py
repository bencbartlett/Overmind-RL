import numpy as np
from screeps_rl_env.processors_multiagent import ScreepsMultiAgentProcessor


class ApproachMultiAgentProcessor(ScreepsMultiAgentProcessor):
    """
    Train a creep to approach the other creep in the room using base movement intents
    """

    def process_state(self, room_state, agent_id):
        # terrain = room_state["terrain"]
        room_objects = room_state["roomObjects"]
        # event_log = room_state["eventLog"]

        my_creep = self.env.agents_dict[agent_id]
        my_creep_name = my_creep.get_full_name(self.env.room)
        my_creep_username = my_creep.player_name

        tombstones_present = any(filter(lambda obj: obj['type'] == 'tombstone', room_objects))

        if tombstones_present:
            return None

        all_creeps = list(filter(lambda obj: obj['type'] == 'creep', room_objects))

        enemies, allies, me = [], [], None
        for creep in all_creeps:
            if creep['username'] != my_creep_username:
                enemies.append(creep)
            else:
                if creep['name'] != my_creep_name:
                    allies.append(creep)
                else:
                    me = creep

        ob = np.concatenate([
            [creep['x'], creep['y']] for creep in [*enemies, *allies, me]
        ])

        self.prev_ob = ob

        return ob

    def process_action(self, action, agent_id):
        creep_name = self.env.agents_dict[agent_id].get_full_name(self.env.room)
        return {creep_name: [["move", int(action) + 1]]}

    def process_reward(self, obs, agent_id):
        my_x, my_y = obs[-2:]
        penalty = 0
        for foe_x, foe_y in zip(obs[0:-2:2], obs[1:-2:2]):
            penalty += (foe_x - my_x) ** 2 + (foe_y - my_y) ** 2

        return 1 / 50 * (50 - np.sqrt(penalty))

    def process_observation(self, state, agent_id):
        """Returns the observation from a room given the state after running self.interface.tick()"""
        ob = self.process_state(state, agent_id)

        if ob is not None:
            return ob, self.process_reward(ob, agent_id), False, {}
        else:
            return self.prev_ob, 0, True, {}
