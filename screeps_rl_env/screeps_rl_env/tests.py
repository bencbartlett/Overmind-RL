import unittest

from screeps_rl_env import ScreepsEnv, ScreepsVectorEnv, ScreepsInterface


class TestScreepsEnv(unittest.TestCase):

    def test_ScreepsInterface(self):
        print("\n\n\nTesting ScreepsInterface...")
        interface = ScreepsInterface(0)
        room = interface.add_env(0)
        interface.reset()

        creep1_name = "Agent1_{}_{}".format(0, 0)
        creep2_name = "Agent2_{}_{}".format(0, 0)

        for tick in range(20):
            actions = {"Agent1": {creep1_name: [["move", tick % 8 + 1]]},
                       "Agent2": {creep2_name: [["move", tick % 8 + 1]]}}
            interface.send_all_actions(actions)
            interface.tick()
            state = interface.get_room_state(room)
            objects = state["roomObjects"]
            [print(obj["name"], obj["x"], obj["y"]) for obj in objects]
        interface.close()

    def test_ScreepsEnv(self):
        print("\n\n\nTesting ScreepsEnv...")
        env = ScreepsEnv(worker_index = 0, vector_index = 0)
        env.reset()

        for tick in range(20):
            action = tick % 8
            ob, reward, done, info = env.step(action)
            print(ob, reward, done, info)

        env.close()

    def test_ScreepsVectorEnv(self, num_envs = 3):
        print("\n\n\nTesting ScreepsVectorEnv...")
        env = ScreepsVectorEnv(worker_index = 0, num_envs = num_envs)
        env.vector_reset()

        for tick in range(20):
            print(tick)
            actions = [tick % 8] * num_envs
            obs, rewards, dones, infos = env.vector_step(actions)
            print(obs, rewards, dones, infos)

        env.reset_at(0)

        for tick in range(5):
            actions = [tick % 8] * num_envs
            obs, rewards, dones, infos = env.vector_step(actions)
            print(obs, rewards, dones, infos)

        env.close()

if __name__ == "__main__":
    unittest.main()
