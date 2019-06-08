import numpy as np

from screeps_rl_env.processors_multiagent import ScreepsMultiAgentProcessor


class ApproachMultiAgentProcessor(ScreepsMultiAgentProcessor):
    """
    Train a creep to approach the other creep in the room using base movement intents
    """

    def process_state(self, room_state, agent_id):
        room_objects = room_state["roomObjects"]

        tombstones_present = any(filter(lambda obj: obj['type'] == 'tombstone', room_objects))

        if tombstones_present:
            return None

        enemies, allies, me = self.get_enemies_allies_me(room_objects, agent_id)

        return np.concatenate([
            [creep['x'], creep['y']] for creep in [*enemies, *allies, me]
        ])

    def process_action(self, action, agent_id):
        creep_name = self.env.agents_dict[agent_id].get_full_name(self.env.room)
        return {creep_name: [["move", int(action) + 1]]}

    def process_reward(self, obs, agent_id):
        my_x, my_y = obs[-2:]
        penalty = 0
        for foe_x, foe_y in zip(obs[0:-2:2], obs[1:-2:2]):
            penalty += max(abs(foe_x - my_x), abs(foe_y - my_y))

        return 1 / 50 * (50 - np.sqrt(penalty))

    def process_observation(self, state, agent_id):
        """Returns the observation from a room given the state after running self.interface.tick()"""
        ob = self.process_state(state, agent_id)

        if ob is not None:
            self.prev_ob[agent_id] = ob
            return ob, self.process_reward(ob, agent_id), False, {}
        else:
            return self.prev_ob[agent_id], 0, True, {}
