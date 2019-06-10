def on_episode_start(info):
    # episode = info["episode"]
    # print("episode {} started".format(episode.episode_id))
    # episode.user_data["pole_angles"] = []
    pass


def on_episode_step(info):
    episode = info["episode"]
    # pole_angle = abs(episode.last_observation_for()[2])
    # raw_angle = abs(episode.last_raw_obs_for()[2])
    # assert pole_angle == raw_angle
    # episode.user_data["pole_angles"].append(pole_angle)
    # obs = episode.last_info_for("Agent0")


def on_episode_end(info, agent_ids):
    episode = info["episode"]

    victory = any(episode.last_info_for(agent_id).get("all_enemies_dead") for agent_id in agent_ids)

    # pole_angle = np.mean(episode.user_data["pole_angles"])
    # print("episode {} ended with length {} and pole angles {}".format(
    #     episode.episode_id, episode.length, pole_angle))
    episode.custom_metrics["victory"] = victory


def on_sample_end(info):
    print("returned sample batch of size {}".format(info["samples"].count))


def on_train_result(info):
    print("trainer.train() result: {} -> {} episodes".format(
        info["trainer"], info["result"]["episodes_this_iter"]))
    # you can mutate the result dict to add new fields to return
    info["result"]["callback_ok"] = True


def on_postprocess_traj(info):
    episode = info["episode"]
    batch = info["post_batch"]
    print("postprocessed {} steps".format(batch.count))
    if "num_batches" not in episode.custom_metrics:
        episode.custom_metrics["num_batches"] = 0
    episode.custom_metrics["num_batches"] += 1