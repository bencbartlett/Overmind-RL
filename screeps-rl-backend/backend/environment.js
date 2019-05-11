const _ = require('lodash');
const fs = require('fs');
const path = require('path');
const {ScreepsServer, TerrainMatrix} = require('./serverMockup/src/main.js');

const C = require('@screeps/driver').constants;

const ROOM = 'W0N1';
const RL_ACTION_SEGMENT = 70;

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
            modfile: path.resolve(appDir, '../serverMockup/assets/mods.json')
        };

        console.log('opts: ' + JSON.stringify(opts));

        this.server = new ScreepsServer(opts);

    }

    /**
     * Resets the server world
     */
    async resetWorld() {
        await this.server.world.reset();
    }

    /**
     * Resets the training environment, reverting server to a single room, setting room terrain, and adding bots
     */
    async resetTrainingEnvironment() {

        // Stop the server
        // await this.stopServer();

        // Clear the database
        await this.resetWorld();

        // Add a single room with specified terrain
        // const terrain = this.getRoomTerrain(roomName);

        // Prepare the terrain for a new room
        const terrain = new TerrainMatrix();
        const walls = [[10, 10], [10, 40], [40, 10], [40, 40]];
        _.each(walls, ([x, y]) => terrain.set(x, y, 'wall'));

        await this.server.world.addRoom(ROOM);
        await this.server.world.setTerrain(ROOM, terrain);

        // Add two players
        const agent1 = await this.addAgent('Agent1', "FF0000");
        const agent2 = await this.addAgent('Agent2', "0000FF");

        // Add a creep to each
        const body = [{type: 'attack', hits: 100, boost: undefined}, {type: 'move', hits: 100, boost: undefined}];

        let [x1, y1] = await this.server.world.getOpenPosition(ROOM);
        await this.createCreep(agent1.id, 'a1c1', body, x1, y1);

        let [x2, y2] = await this.server.world.getOpenPosition(ROOM);
        await this.createCreep(agent2.id, 'a2c1', body, x2, y2);

        // Start the server

        await this.startServer();

    }

    async addAgent(username, badgeColor = undefined) {

        const _script = `module.exports.loop = function() {
		        console.log('Tick!',Game.time);
		        const directions = [TOP, TOP_RIGHT, RIGHT, BOTTOM_RIGHT, BOTTOM, BOTTOM_LEFT, LEFT, TOP_LEFT];
		        console.log('My creeps: ', _.map(Game.creeps, creep => creep.name + ' ' + creep.pos));
		        RawMemory.setActiveSegments([70, 71]);
		        if (RawMemory.segments[71]) {
		            RawMemory.segments[71] = {test: Game.time};
		        }
		        console.log('Memory ', JSON.stringify(Memory));
		        console.log('Segment 70: ', RawMemory.segments[70]);
		        console.log('Segment 71: ', RawMemory.segments[71]);
		        _.each(Game.creeps, c => c.move(_.sample(directions)));
		    };`;

        const modules = {
            main: _script,
        };

        const bot = await this.server.world.addHeadlessBot({username, modules, badgeColor});

        // Print console logs every tick
        bot.on('console', (logs, results, userid, username) => {
            _.each(logs, line => console.log(`[console|${username}]`, line));
        });

        return bot;
    }

    async createCreep(player, name, body, x, y) {
        const energyCapacity = _.sumBy(body, part => part.type === 'carry' ? 50 : 0);

        const creep = {
            name: name,
            x: x,
            y: y,
            body,
            energy: 0,
            energyCapacity: energyCapacity,
            type: 'creep',
            room: ROOM,
            user: player,
            hits: body.length * 100,
            hitsMax: body.length * 100,
            spawning: false,
            fatigue: 0,
            notifyWhenAttacked: true
        };

        await this.server.world.addRoomObject(creep.room, creep.type, creep.x, creep.y, creep);

    }

    // async initializeServer() {
    //
    // 	// Initialize server
    // 	await this.server.world.reset(); // reset world but add invaders and source keepers bots
    //
    // 	// Prepare the terrain for a new room
    // 	const terrain = new TerrainMatrix();
    // 	const walls = [[10, 10], [10, 40], [40, 10], [40, 40]];
    // 	_.each(walls, ([x, y]) => terrain.set(x, y, 'wall'));
    //
    // 	// Create a new room with terrain and basic objects
    // 	await this.server.world.addRoom(ROOM);
    // 	await this.server.world.setTerrain(ROOM, terrain);
    // 	await this.server.world.addRoomObject(ROOM, 'controller', 10, 10, {level: 0});
    // 	await this.server.world.addRoomObject(ROOM, 'source', 10, 40, {
    // 		energy: 1000,
    // 		energyCapacity: 1000,
    // 		ticksToRegeneration: 300
    // 	});
    // 	await this.server.world.addRoomObject(ROOM, 'mineral', 40, 40, {
    // 		mineralType: 'H',
    // 		density: 3,
    // 		mineralAmount: 3000
    // 	});
    //
    // 	// Add a bot in W0N1
    // 	// const overmindPath = path.resolve(__dirname, '../bots/overmind.js');
    // 	// const script = fs.readFileSync(overmindPath, 'utf8');
    //
    // 	const _script = `module.exports.loop = function() {
    // 	        console.log('Tick!',Game.time);
    // 	        const directions = [TOP, TOP_RIGHT, RIGHT, BOTTOM_RIGHT, BOTTOM, BOTTOM_LEFT, LEFT, TOP_LEFT];
    // 	        _.sample(Game.spawns).createCreep([MOVE]);
    // 	        _.each(Game.creeps, c => c.move(_.sample(directions)));
    // 	    };`;
    //
    // 	// console.log(script);
    // 	const modules = {
    // 		main: _script,
    // 	};
    // 	const bot = await this.server.world.addBot({username: 'bot', room: ROOM, x: 25, y: 25, modules});
    //
    // 	// Print console logs every tick
    // 	bot.on('console', (logs, results, userid, username) => {
    // 		_.each(logs, line => console.log(`[console|${username}]`, line));
    // 	});
    //
    // }

    // Data retrieval methods ==================================================

    /**
     * Returns the terrain for a room, serialized to a 2500-char string by
     * default
     */
    async getRoomTerrain(roomName = ROOM, serialized = true) {
        const terrain = await this.server.world.getTerrain(roomName);
        if (serialized) {
            return terrain.serialize();
        } else {
            return terrain;
        }
    }

    /**
     * Set the contents of a user's memory segment
     */
    async setMemorySegment(username, segment, contents) {
        const {db, env} = await this.server.world.load();
        const {_id} = await db.users.findOne({username: username});
        console.log(`Setting user ${username} with id ${_id} segment ${segment} to ${contents}`);
        await env.hset(env.keys.MEMORY_SEGMENT + _id, segment, contents);
        const seg = await env.hget(env.keys.MEMORY_SEGMENT + _id, segment);
        console.log(`Segment: ${seg}`)
    }

    /**
     * Set the contents of a user's memory
     */
    async setMemory(username, contents) {
        const {db, env} = await this.server.world.load();
        const {_id} = await db.users.findOne({username: username});
        console.log(`Setting user memory ${username} with id ${_id} to ${contents}`);
        await env.set(env.keys.MEMORY + _id, contents);
        const mem = await env.get(env.keys.MEMORY + _id);
        console.log(`Memory: ${mem}`)
    }

    /**
     * Returns a list of room objects for a room
     */
    async getRoomObjects(roomName = ROOM) {
        return await this.server.world.getRoomObjects(roomName);
    }

    async getEventLog(roomName = ROOM) {
        return await this.server.world.getEventLog(roomName);
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