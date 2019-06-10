from abc import ABC, abstractmethod
from typing import Dict, Tuple, List, Any

import numpy as np

EVENT_ATTACK = 1
EVENT_OBJECT_DESTROYED = 2
EVENT_ATTACK_CONTROLLER = 3
EVENT_BUILD = 4
EVENT_HARVEST = 5
EVENT_HEAL = 6
EVENT_REPAIR = 7
EVENT_RESERVE_CONTROLLER = 8
EVENT_UPGRADE_CONTROLLER = 9
EVENT_EXIT = 10

EVENT_ATTACK_TYPE_MELEE = 1
EVENT_ATTACK_TYPE_RANGED = 2
EVENT_ATTACK_TYPE_RANGED_MASS = 3
EVENT_ATTACK_TYPE_DISMANTLE = 4
EVENT_ATTACK_TYPE_HIT_BACK = 5
EVENT_ATTACK_TYPE_NUKE = 6

EVENT_HEAL_TYPE_MELEE = 1
EVENT_HEAL_TYPE_RANGED = 2


class ScreepsMultiAgentProcessor(ABC):
    """
    Processors are a class which provides post-processing methods for interpreting room states and generating rewards.
    They can be interchangeably dropped into the Screeps environment.
    """

    def __init__(self, env):
        from screeps_rl_env import ScreepsMultiAgentEnv  # local import needed to prevent circular dependencies
        self.env: ScreepsMultiAgentEnv = env
        self.prev_ob: Dict[str, np.ndarray] = {}

    @staticmethod
    @abstractmethod
    def get_spaces(agents):
        """
        Yields the observation and action spaces; convenient for fetching spaces without instantiatng an environment
        :param agents: list of agents that would instantiate the ScreepsMultiAgentEnv
        :return: observation_space, action_space
        """
        raise NotImplementedError

    def get_creeps(self, room_objects: List, include_tombstones=True) -> List[Dict]:
        """
        Get a list of room objects which are creeps
        :param room_objects: room objects for the environment room
        :param include_tombstones: whether or not to include tombstones in the return (to track dead creeps)
        :return: objects which are creeps (or tombstones)
        """
        if include_tombstones:
            return list(filter(lambda obj: obj['type'] == 'creep' or obj['type'] == 'tombstone', room_objects))
        else:
            return list(filter(lambda obj: obj['type'] == 'creep', room_objects))

    def get_allies(self, room_objects: List, agent_id: str, include_self=False) -> List[Dict]:
        """
        Returns a list of allied creeps given room objects
        :param room_objects: room objects for the environment room
        :param agent_id: id of the agent to be compared to
        :param include_self: whether or not to include the agent itself in the list
        :return: all allied creeps
        """
        all_creeps = self.get_creeps(room_objects)

        creep = self.env.agents_dict[agent_id]
        creep_name = creep.get_full_name(self.env.room)
        creep_owner = creep.player_name

        if include_self:
            return list(filter(lambda creep: creep['username'] == creep_owner, all_creeps))
        else:
            return list(filter(lambda creep: creep['username'] == creep_owner and
                                             creep['name'] != creep_name,
                               all_creeps))

    def get_enemies(self, room_objects: List, agent_id: str) -> List[Dict]:
        """
        Returns a list of enemy creeps given room objects
        :param room_objects: room objects for the environment room
        :param agent_id: id of the agent to be compared to
        :return: all enemy creeps
        """
        all_creeps = self.get_creeps(room_objects)

        owner = self.env.agents_dict[agent_id].player_name

        return list(filter(lambda creep: creep['username'] == owner, all_creeps))

    def get_enemies_allies_me(self, room_objects: List, agent_id: str,
                              include_tombstones=True) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        Given room objects and an agent id, return a tuple of (enemy creeps, allied creeps, self) sorted by name
        :param room_objects: room objects for the environment room (can contain non-creep objects)
        :param include_tombstones: whether or not to include tombstones in the return (to track dead creeps)
        :param agent_id: id of the agent to be compared to
        :return: all enemy creeps
        """

        creep = self.env.agents_dict[agent_id]
        creep_name = creep.get_full_name(self.env.room)
        creep_owner = creep.player_name

        all_creeps = self.get_creeps(room_objects, include_tombstones=include_tombstones)

        enemies, allies, me = [], [], None

        for creep in all_creeps:
            username = creep.get('username') or self.env.user_id_to_username[creep['user']]
            if username != creep_owner:
                enemies.append(creep)
            else:
                other_creep_name = creep.get('name') or creep.get('creepName')
                if other_creep_name != creep_name:
                    allies.append(creep)
                else:
                    me = creep

        enemies.sort(key=lambda creep: creep.get('name') or creep.get('creepName'))
        allies.sort(key=lambda creep: creep.get('name') or creep.get('creepName'))

        return enemies, allies, me

    def is_agent_alive(self, room_objects: List, agent_id: str) -> bool:
        creep_name = self.env.agents_dict[agent_id].get_full_name(self.env.room)

        creeps = self.get_creeps(room_objects, include_tombstones=False)
        return any(other_name == creep_name for other_name in map(lambda creep: creep['name'], creeps))

    def parse_event_log(self, event_log: List[Dict]):
        attack_events, heal_events, destroy_events = [], [], []

        for event in event_log:
            if event["event"] == EVENT_ATTACK:
                attack_events.append(event)
            elif event["event"] == EVENT_HEAL:
                heal_events.append(event)
            elif event["event"] == EVENT_OBJECT_DESTROYED:
                destroy_events.append(event)

        return attack_events, heal_events, destroy_events

    def get_damage_done_last_tick(self, event_log: List[Dict], creep_object_id: str) -> int:
        """
        Gets the total amount of damage a creep dealt last tick
        :param event_log: event log for the room
        :param creep_object_id: the Game object id for the creep (NOT Creep.agent_id)
        :return: amount of damage dealt
        """
        attack_events, _, _ = self.parse_event_log(event_log)
        damage_dealt = 0
        for event in attack_events:
            if event["objectId"] == creep_object_id:
                damage_dealt += event["data"]["damage"]
        return damage_dealt

    def get_deaths_contributed_to(self, event_log: List[Dict], creep_object_id: str) -> List[Dict]:
        """
        Gets a list of death events which the creep directly contributed to
        :param event_log: event log for the room
        :param creep_object_id: the Game object id for the creep (NOT Creep.agent_id)
        :return: amount of damage dealt
        """
        attack_events, _, death_events = self.parse_event_log(event_log)
        attack_targets = []
        for attack_event in attack_events:
            if attack_event["objectId"] == creep_object_id:
                attack_targets.append(attack_event["data"]["targetId"])

        return list(filter(lambda death_event: death_event["objectId"] in attack_targets, death_events))

    def get_enemy_deaths(self, event_log: List[Dict], agent_id: str) -> List[Dict]:
        death_events = []
        agent_owner = self.env.agents_dict[agent_id].player_name
        _, _, destroy_events = self.parse_event_log(event_log)
        for event in destroy_events:
            id = event["objectId"]
            owner = self.env.id_ownership.get(id)
            if owner is not None and owner != agent_owner:
                death_events.append(event)
        return death_events

    def get_allied_deaths(self, event_log: List[Dict], agent_id: str) -> List[Dict]:
        death_events = []
        agent_owner = self.env.agents_dict[agent_id].player_name
        _, _, destroy_events = self.parse_event_log(event_log)
        for event in destroy_events:
            id = event["objectId"]
            owner = self.env.id_ownership.get(id)
            if owner == agent_owner:
                death_events.append(event)
        return death_events

    @abstractmethod
    def process_action(self, action: int, agent_id: str) -> Dict:
        """
        Process an action, returning a command to be written to Overmind memory to tell the agent what to do
        :param action: int, direction to move (0-7, inclusive)
        :param agent_id: the name of the creep to receive the processed input
        :return: JSON-formatted command to tell the creep to move
        """
        raise NotImplementedError

    @abstractmethod
    def get_observation(self, room_state: Dict, agent_id: str) -> Any:
        """
        Yield the observation for the current tick given a room state and agent id
        :param room_state: the state of the room
        :param agent_id: the name of the creep to receive the processed input
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def get_reward(self, room_state: Dict, agent_id: str) -> float:
        """
        Yield the reward for the current tick given a room state and agent id
        :param room_state: the state of the room
        :param agent_id: the name of the creep to receive the processed input
        :return: reward (float)
        """
        raise NotImplementedError

    @abstractmethod
    def process_state(self, room_state: Dict, agent_id: str) -> Tuple[Any, float, bool, Dict]:
        """
        Returns the observation, reward, termination, and info for an agent given the state of the room
        :param room_state: dict, room state
        :param agent_id: the name of the creep to receive the processed input
        :return: ob, reward, done, info
        """
        raise NotImplementedError
