const _ = require('lodash');
const fs = require('fs');
const path = require('path');
const {ScreepsServer, TerrainMatrix} = require('./serverMockup/src/main.js');

const C = require('@screeps/driver').constants;

const ROOM = 'E0S0'; // default room to use for single room
const WORLD_WIDTH = 10; // max width of the world; must be even

// const OVERMIND_PATH = "../../../Overmind/dist/main.js";

class ScreepsEnvironment {

    /**
     * Create an instance of the remote ScreepsEnvironment
     */
    constructor(index) {
        this.index = index;
        this.serverPort = 21025 + 5 * index;
        this.commsPort = 22025 + 5 * index;

        // Start the server
        const appDir = require.main ? path.dirname(require.main.filename) : __dirname;
        const opts = {
            path: path.resolve(appDir, '../../servers', `server${this.index}`),
            logdir: path.resolve(appDir, '../../servers', `server${this.index}`, 'logs'),
            assetsDir: path.resolve(appDir, '../../servers', `server${this.index}`, 'assets'),
            port: this.serverPort,
            commsPort: this.commsPort,
            modfile: path.resolve(appDir, '../serverMockup/assets/mods.json')
        };

        console.log('opts: ' + JSON.stringify(opts));

        this.server = new ScreepsServer(opts);

        this.agent1 = undefined;
        this.agent2 = undefined;

        // List of vector_index entries that correspond to new rooms
        this.roomIndices = [];
    }

    /**
     * Adds a room "environment" to the screeps world (used for vectorized
     * Python environments)
     */
    async addEnv(index) {
        if (this.roomIndices.includes(index)) {
            throw new Error(`Cannot add room environment with vector_index ${index}! ` +
                `this.index = ${this.index}; this.roomIndices = ${this.roomIndices}`);
        } else {
            this.roomIndices.push(index);
            if (this.server.started) {
                const room = ScreepsEnvironment._roomFromIndex(index);
                await this.addRoom(room);
                await this.resetRoom(room);
            }
        }
        return ScreepsEnvironment._roomFromIndex(index);
    }

    // addEnv(index) {
    //     // if (index === undefined) {
    //     //     index = this.roomIndices.length;
    //     // }
    //     if (this.roomIndices.includes(index)) {
    //         throw new Error(`Cannot add room environment with vector_index ${index}! ` +
    //             `this.index = ${this.index}; this.roomIndices = ${this.roomIndices}`);
    //     } else if (this.server.started) {
    //         throw new Error(`ScreepsEnvironment.addEnv() can only be called before starting server!`)
    //     } else {
    //         this.roomIndices.push(index);
    //     }
    //     return ScreepsEnvironment._roomFromIndex(index);
    // }

    /**
     * Lists the names of all rooms in the simulation
     */
    listRoomNames() {
        return _.map(this.roomIndices, index => ScreepsEnvironment._roomFromIndex(index));
    }

    /**
     * Gets a room name from an index. Rooms start at ROOM and are enumerated
     * in checkerboard reading order, wrapping once E*-- reaches WORLD_WIDTH
     */
    static _roomFromIndex(index) {
        let x = index % (WORLD_WIDTH / 2);
        let y = Math.floor(index / (WORLD_WIDTH / 2));
        if (y % 2 === 0) {
            x = 2 * x
        } else {
            x = 2 * x + 1
        }
        return "E" + x.toString(10) + "S" + y.toString(10);
    }

    /**
     * Inverse of _roomFromIndex(); gets an index given a room name
     */
    static _indexFromRoom(room) {
        const coordinateRegex = /(E|W)(\d+)(N|S)(\d+)/g;
        const match = coordinateRegex.exec(room);

        const xDir = match[1];
        const x = match[2];
        const yDir = match[3];
        const y = match[4];

        return y * (WORLD_WIDTH / 2) + Math.floor(x / 2);
    }

    /**
     * Terrain generation function
     */
    static generateTerrain() {
        const terrain = new TerrainMatrix();
        const walls = [[10, 10], [10, 40], [40, 10], [40, 40]];
        _.each(walls, ([x, y]) => terrain.set(x, y, 'wall'));
        return terrain;
    }

    /**
     * Adds a room to the world, optionally setting the terrain
     */
    async addRoom(roomName, terrain = undefined) {
        await this.server.world.addRoom(roomName);
        await this.setRoomTerrain(roomName, terrain);
    }

    /**
     * Resets a specified room, deleting all creeps and spawning in new ones.
     * Can be called while server is running.
     */
    async resetRoom(roomName, creepConfig = null) {

        const gameTime = await this.server.world.gameTime;

        console.log(`[${gameTime}] Resetting environment ${this.index}, room ${roomName}`);

        await this.deleteRoomCreeps(roomName);

        if (creepConfig) {
            creepConfig = JSON.parse(creepConfig);
        }

        if (creepConfig != null) {
            // Manually specified list of creep initial setups
            for (let creep of creepConfig) {
                let {player_name, creep_index, body, x_init, y_init} = creep;

                let x, y;
                if (x_init == null || y_init == null) {
                    [x, y] = await this.server.world.getOpenPosition(roomName);
                } else {
                    [x, y] = [x_init, y_init];
                }

                let agent;
                if (player_name === "Agent1") {
                    agent = this.agent1;
                } else if (player_name === "Agent2") {
                    agent = this.agent2;
                } else {
                    throw new Error(`Invalid player_name: ${player_name}`)
                }

                let name = `${player_name}_${creep_index}:${roomName}`;

                await this.createCreep(agent, roomName, x, y, name, body);
            }
        } else {
            let [x1, y1] = await this.server.world.getOpenPosition(roomName);
            await this.createCreep(this.agent1, roomName, x1, y1);

            let [x2, y2] = await this.server.world.getOpenPosition(roomName);
            await this.createCreep(this.agent2, roomName, x2, y2);
        }

        // Clear the event log
        await this.clearEventLog(roomName);

    }

    /**
     * Resets the training environment, reverting server to a single room, setting room terrain, and adding bots
     */
    async resetTrainingEnvironment() {

        console.log(`\n===== RESETTING TRAINING ENVIRONMENT ${this.index} =====\n`);

        // Clear the database
        await this.server.world.reset();

        // Add two players
        const agent1 = await this.addAgent('Agent1', "FF0000");
        const agent2 = await this.addAgent('Agent2', "0000FF");

        this.agent1 = agent1;
        this.agent2 = agent2;

        // Add and reset each room
        if (this.roomIndices.length === 0) {
            throw new Error(`No rooms have been requested! Use ScreepsEnvironment.addEnv() to add a room environment.`)
        }
        for (let index of this.roomIndices) {
            const room = ScreepsEnvironment._roomFromIndex(index);
            await this.addRoom(room);
            await this.resetRoom(room);
        }

        // Start the server
        await this.startServer();

    }

    async addAgent(username, badgeColor = undefined) {

        const overmindPath = path.resolve(__dirname, '../bots/overmind.js');

        // TODO: can build Overmind from source
        // const overmindPath = path.resolve(__dirname, '../../../Overmind/dist/main.js');

        const script = fs.readFileSync(overmindPath, 'utf8');

        const _script = `module.exports.loop = function() {
		        console.log('Tick!',Game.time);
		        const directions = [TOP, TOP_RIGHT, RIGHT, BOTTOM_RIGHT, BOTTOM, BOTTOM_LEFT, LEFT, TOP_LEFT];
		        console.log('My creeps: ', _.map(Game.creeps, creep => creep.name + ' ' + creep.pos));
		        RawMemory.setActiveSegments([70, 71]);
		        if (RawMemory.segments[71]) {
		            RawMemory.segments[71] = {test: Game.time};
		        }
		        console.log('Memory ', JSON.stringify(Memory));
		        console.log('Segment 70: ', JSON.stringify(RawMemory.segments[70]));
		        console.log('Segment 71: ', RawMemory.segments[71]);
		        console.log('Shard: ', Game.shard.name);
		        _.each(Game.creeps, c => c.move(_.sample(directions)));
		    };`;

        const modules = {
            main: script,
        };

        const bot = await this.server.world.addHeadlessBot({username, modules, badgeColor});

        // Print console logs every tick
        bot.on('console', (logs, results, userid, username) => {
            _.each(logs, line => console.log(`[console|${username}]`, line));
        });

        return bot;
    }

    async generateCreepName(agent, roomName) {
        // const roomIndex = ScreepsEnvironment._indexFromRoom(roomName);
        const creepsInRoom = await this.server.world.getRoomCreeps(roomName, agent.id);
        const creepIndex = creepsInRoom.length;
        return `${agent.username}_${creepIndex}:${roomName}`
    }

    static generateCreepBody() {
        // Add a creep to each
        const body = [
            {type: 'attack', hits: 100, boost: undefined},
            {type: 'rangedAttack', hits: 100, boost: undefined},
            {type: 'heal', hits: 100, boost: undefined},
            {type: 'move', hits: 100, boost: undefined},
            {type: 'move', hits: 100, boost: undefined},
            {type: 'move', hits: 100, boost: undefined},
        ];
        return body;
    }

    async createCreep(agent, room, x, y, name = undefined, body = undefined, lifetime = 100) {

        if (!name) {
            name = await this.generateCreepName(agent, room)
        }
        if (!body) {
            body = ScreepsEnvironment.generateCreepBody();
        }

        const energyCapacity = _.sumBy(body, part => part.type === 'carry' ? 50 : 0);

        const gameTime = await this.server.world.gameTime;

        const creep = {
            name: name,
            x: x,
            y: y,
            body: body,
            energy: 0,
            energyCapacity: energyCapacity,
            type: 'creep',
            room: room,
            user: agent.id,
            username: agent.username, // not part of standard creep db entries
            hits: body.length * 100,
            hitsMax: body.length * 100,
            spawning: false,
            fatigue: 0,
            ageTime: lifetime + gameTime,
            notifyWhenAttacked: true
        };

        await this.server.world.addRoomObject(creep.room, creep.type, creep.x, creep.y, creep);

    }

    /**
     * Triggers reset of global for all users
     */
    async triggerAllGlobalResets() {
        console.log(`----- Triggering global resets! -----`);
    	await this.server.world.triggerGlobalReset(this.agent1);
    	await this.server.world.triggerGlobalReset(this.agent2);
    }

    /**
     * Returns the terrain for a room, serialized to a 2500-char string by
     * default
     */
    async getRoomTerrain(roomName, serialized = true) {
        const terrain = await this.server.world.getTerrain(roomName);
        if (serialized) {
            return terrain.serialize();
        } else {
            return terrain;
        }
    }

    /**
     * Sets the terrain for a room and resets global for each user to trigger
     * recache of terrain data
     */
    async setRoomTerrain(roomName, terrain=undefined) {
        if (!terrain) {
            terrain = ScreepsEnvironment.generateTerrain();
        }
        await this.server.world.setTerrain(roomName, terrain);
        await this.triggerAllGlobalResets();
    }

    /**
     * Returns the terrain for a room, serialized to a 2500-char string by
     * default
     */
    async getAllRoomTerrain(serialized = true) {
        const allTerrain = await this.server.world.getAllTerrain();
        if (serialized) {
            return _.mapValues(allTerrain, terrain => terrain.serialize());
        } else {
            return allTerrain;
        }
    }

    /**
     * Set the contents of a user's memory segment
     */
    async setMemorySegment(username, segment, contents) {
        const {db, env} = await this.server.world.load();
        const {_id} = await db.users.findOne({username: username});
        console.log(`Setting user ${username} with id ${_id} segment ${segment} to ${contents}`);
        await env.hset(env.keys.MEMORY_SEGMENTS + _id, segment, contents);
        const seg = await env.hget(env.keys.MEMORY_SEGMENTS + _id, segment);
        console.log(`Segment: ${seg}`)
    }

    /**
     * Set the contents of a user's memory
     */
    async setMemory(username, contents) {
        const {db, env} = await this.server.world.load();
        const {_id} = await db.users.findOne({username: username});
        // console.log(`Setting user memory ${username} with id ${_id} to ${contents}`);
        await env.set(env.keys.MEMORY + _id, contents);
        const mem = await env.get(env.keys.MEMORY + _id);
        // console.log(`Memory: ${mem}`)
    }

    /**
     * Set the contents of a user's Memory.reinforcementLearning object
     */
    async sendCommands(username, contents) {
        const rlObjectStringified = '{"reinforcementLearning":' + contents + '}';
        await this.setMemory(username, rlObjectStringified);
    }

    /**
     * Returns a list of room objects for a room
     */
    async getRoomObjects(roomName) {
        return await this.server.world.getRoomObjects(roomName);
    }

    /**
     * Returns an object containing room objects for each room indexed by room name
     */
    async getAllRoomObjects() {
        const allRoomObjects = await this.server.world.getAllRoomObjects();
        return _.groupBy(allRoomObjects, roomObject => roomObject.room);
    }

    /**
     * Delete all roomObjects within a room
     */
    async deleteRoomObjects(roomName) {
        return await this.server.world.deleteRoomObjects(roomName);
    }

    /**
     * Delete all creeps within a room
     */
    async deleteRoomCreeps(roomName) {
        return await this.server.world.deleteRoomCreeps(roomName);
    }

    async getEventLog(roomName) {
        return await this.server.world.getEventLog(roomName);
    }

    async clearEventLog(roomName) {
        return await this.server.world.setEventLog(roomName, "[]");
    }

    async getAllEventLogs() {
        return await this.server.world.getAllEventLogs();
    }

    async startBackend() {
        await this.server.startBackend();
    }

    async tick() {
        return await this.server.tick();
    }

    async startServer() {
        await this.server.start();
    }

    async stopServer() {
        this.server.stop();
    }

    exit() {
        this.server.kill();
        process.exit();
    }

}

module.exports = ScreepsEnvironment;