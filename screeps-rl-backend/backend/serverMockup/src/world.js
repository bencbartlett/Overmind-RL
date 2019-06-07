/* eslint function-paren-newline: "off" */

const _ = require('lodash');
const util = require('util');
const zlib = require('zlib');
const TerrainMatrix = require('./terrainMatrix');
const User = require('./user');
const map = require('@screeps/backend/lib/cli/map');

class World {

	/**
	 * Constructor
	 */
	constructor(server) {
		this.server = server;
	}

	/**
	 * Getters
	 */
	get gameTime() {
		return this.load().then(({env}) => env.get('gameTime'));
	}

	/**
	 * Connect to server (if needed) and return constants, database, env and pubsub objects
	 */
	async load() {
		if (!this.server.connected) await this.server.connect();
		const {db, env, pubsub} = this.server.common.storage;
		const C = this.server.constants;
		return {C, db, env, pubsub};
	}

	/**
	 * Set rom status (and create it if needed)
	 * This function does NOT generate terrain data
	 */
	async setRoom(room, status = 'normal', active = true) {
		const {db} = this.server.common.storage;
		const data = await db.rooms.find({_id: room});
		if (data.length > 0) {
			await db.rooms.update({_id: room}, {$set: {status, active}});
		} else {
			await db.rooms.insert({_id: room, status, active});
		}
		await this.server.driver.updateAccessibleRoomsList();
	}

	/**
	 * Simplified allias for setRoom()
	 */
	async addRoom(room) {
		return this.setRoom(room);
	}

	/**
	 * Get a random unoccupied position in a room
	 */
	async getOpenPosition(room) {
		const terrain = await this.getTerrain(room);
		const objects = await this.getRoomObjects(room);
		let okPos = false;
		let x, y;
		while (!okPos) {
			okPos = true;

			// get a random position not on edges
			x = _.random(1, 49);
			y = _.random(1, 49);

			// make sure it's not on a wall
			if (terrain.get(x, y) === 'wall') {
				okPos = false;
			}

			// make sure there's nothing blocking movement
			for (let obj of objects) {
				if (obj.x === x && obj.y === y) {
					if (!(obj.type === 'road' || obj.type === 'container' /* TODO: friendly ramparts */)) {
						okPos = false;
					}
				}
			}
		}
		return [x, y];
	}

	/**
	 * Return room terrain data (walls, plains and swamps)
	 * Return a TerrainMatrix instance
	 */
	async getTerrain(room) {
		const {db} = this.server.common.storage;
		// Load data
		const data = await db['rooms.terrain'].find({room});
		// Check if data actually exists
		if (data.length === 0) {
			throw new Error(`room ${room} doesn't appear to have any terrain data`);
		}
		// Parse and return terrain data as a TerrainMatrix
		const serial = _.get(_.first(data), 'terrain');
		return TerrainMatrix.unserialize(serial);
	}

	/**
	 * Return room terrain data (walls, plains and swamps)
	 * Return a TerrainMatrix instance
	 */
	async getAllTerrain() {
		const {db} = this.server.common.storage;
		// Load data
		const data = await db['rooms.terrain'].find();

		// Parse and return terrain data as a TerrainMatrix
		let allTerrain = {};
		for (let roomData of data) {
			const serial = _.get(roomData, 'terrain');
			allTerrain[roomData.room] = TerrainMatrix.unserialize(serial);
		}
		return allTerrain;
	}

	/**
	 * Define room terrain data (walls, plains and swamps)
	 * @terrain must be an instance of TerrainMatrix.
	 */
	async setTerrain(room, terrain = new TerrainMatrix()) {
		const {db, env} = this.server.common.storage;
		// Check parameters
		if (!(terrain instanceof TerrainMatrix)) {
			throw new Error('@terrain must be an instance of TerrainMatrix');
		}
		// Insert or update data in database
		const data = await db['rooms.terrain'].find({room});
		if (data.length > 0) {
			await db['rooms.terrain'].update({room}, {$set: {terrain: terrain.serialize()}});
		} else {
			await db['rooms.terrain'].insert({room, terrain: terrain.serialize()});
		}
		// Update environment cache
		await this.updateEnvTerrain(db, env);
		// Update the map images
		await map.updateRoomImageAssets(room);
	}

	/**
	 * Load (if needed) and return constants, database, env and pubsub objects
	 */
	async addRoomObject(room, type, x, y, attributes) {
		const {db} = this.server.common.storage;
		// Check parameters
		if (x < 0 || y < 0 || x >= 50 || y >= 50) {
			throw new Error('invalid x/y coordinates (they must be between 0 and 49)');
		}
		// Inject data in database
		const object = Object.assign({room, x, y, type}, attributes);
		return db['rooms.objects'].insert(object);
	}

	/**
	 * Delete all roomObjects within a room
	 */
	async deleteRoomObjects(roomName) {
		const {db} = await this.load();
		return await db['rooms.objects'].removeWhere({room: roomName});
	}

	/**
	 * Delete all creeps within a room
	 */
	async deleteRoomCreeps(roomName, deleteTombstones = true) {
		const {db} = await this.load();
		if (deleteTombstones) {
			await db['rooms.objects'].removeWhere({room: roomName, type: 'tombstone'});
		}
		return await db['rooms.objects'].removeWhere({room: roomName, type: 'creep'});
	}

	/**
	 * Get the roomObjects list for requested roomName
	 */
	async getRoomObjects(roomName) {
		const {db} = await this.load();
		return await db['rooms.objects'].find({room: roomName});
	}

	/**
	 * Get the roomObjects list all rooms
	 */
	async getAllRoomObjects() {
		const {db} = await this.load();
		return await db['rooms.objects'].find();
	}

	/**
	 * Get a list of creeps in the requested roomName
	 */
	async getRoomCreeps(roomName, playerID = undefined) {
		const {db} = await this.load();
		if (playerID) {
			return await db['rooms.objects'].find({room: roomName, type: 'creep', user: playerID});
		} else {
			return await db['rooms.objects'].find({room: roomName, type: 'creep'});
		}
	}

	/**
	 * Gets an event log for a specified room
	 */
	async getEventLog(roomName) {
		const {env} = await this.load();
		return await env.hget(env.keys.ROOM_EVENT_LOG, roomName);
	}

	/**
	 * Sets an event log for a specified room
	 */
	async setEventLog(roomName, newLog = '[]') {
		const {env} = await this.load();
		return await env.hset(env.keys.ROOM_EVENT_LOG, roomName, newLog);
	}

	/**
	 * Gets event logs for all rooms; returns an object indexed by room name
	 */
	async getAllEventLogs() {
		const {env} = await this.load();
		return await env.get(env.keys.ROOM_EVENT_LOG);
	}

	/**
	 * Reset world data to a barren world with invaders and source keepers users
	 */
	async reset() {

		const {db, env} = await this.load();

		// Clear existing room caches
		const rooms = await db.rooms.find({});
		await Promise.all(rooms.map(room => env.del(env.keys.MAP_VIEW + room._id)));

		// Clear database
		await Promise.all(_.map(db, col => col.clear()));
		await env.set('gameTime', 1);

		// // Generate basic terrain data
		// const terrain = new TerrainMatrix();
		// const walls = [[10, 10], [10, 40], [40, 10], [40, 40]];
		// _.each(walls, ([x, y]) => terrain.set(x, y, 'wall'));

		// Insert basic room data
		await Promise.all([
							  db.users.insert({
												  _id         : '2',
												  username    : 'Invader',
												  cpu         : 100,
												  cpuAvailable: 10000,
												  gcl         : 13966610.2,
												  active      : 0
											  }),
							  db.users.insert({
												  _id         : '3',
												  username    : 'Source Keeper',
												  cpu         : 100,
												  cpuAvailable: 10000,
												  gcl         : 13966610.2,
												  active      : 0
											  })
						  ]);
	}

	/**
	 * Stub a basic world by adding 9 plausible rooms with sources, minerals and controllers
	 */
	async stubWorld() {
		// Clear database
		await this.reset();
		// Utility functions
		const addRoomObjects = (roomName, objects) => Promise.all(
			objects.map(o => this.addRoomObject(roomName, o.type, o.x, o.y, o.attributes))
		);
		const addRoom = (roomName, terrain, roomObjects) => Promise.all([
																			this.addRoom(roomName),
																			this.setTerrain(roomName, terrain),
																			addRoomObjects(roomName, roomObjects)
																		]);
		// Add rooms
		const rooms = require('../assets/rooms.json'); // eslint-disable-line global-require
		await Promise.all(_.map(rooms, (data, roomName) => {
			const terrain = TerrainMatrix.unserialize(data.serial);
			return addRoom(roomName, terrain, data.objects);
		}));
	}

	/**
	 * Add a new user to the world
	 */
	async addBot({username, room, x, y, gcl = 1, cpu = 100, cpuAvailable = 10000, active = 10000, spawnName = 'Spawn1', modules = {}}) {
		const {C, db, env} = await this.load();
		// Ensure that there is a controller in requested room
		const data = await db['rooms.objects'].findOne({$and: [{room}, {type: 'controller'}]});
		if (data == null) {
			throw new Error(`cannot add user in ${room}: room does not have any controller`);
		}
		// Insert user and update data
		const user = await db.users.insert({username, cpu, cpuAvailable, gcl, active});
		await Promise.all([
							  env.set(env.keys.MEMORY + user._id, '{}'),
							  db.rooms.update({_id: room}, {$set: {active: true}}),
							  db['users.code'].insert({user: user._id, branch: 'default', modules, activeWorld: true}),
							  db['rooms.objects'].update({room, type: 'controller'}, {
								  $set: {
									  user         : user._id,
									  level        : 1,
									  progress     : 0,
									  downgradeTime: null,
									  safeMode     : 20000
								  }
							  }),
							  db['rooms.objects'].insert({
															 room,
															 type              : 'spawn',
															 x,
															 y,
															 user              : user._id,
															 name              : spawnName,
															 energy            : C.SPAWN_ENERGY_START,
															 energyCapacity    : C.SPAWN_ENERGY_CAPACITY,
															 hits              : C.SPAWN_HITS,
															 hitsMax           : C.SPAWN_HITS,
															 spawning          : null,
															 notifyWhenAttacked: true
														 }),
						  ]);
		// Subscribe to console notificaiton and return emitter
		return new User(this.server, user).init();
	}

	/**
	 * Add a new user to the world without adjusting room properties
	 */
	async addHeadlessBot({
							 username,
							 gcl = 1,
							 cpu = 300,
							 cpuAvailable = 10000,
							 active = 10000,
							 modules = {},
							 badgeColor = undefined,
							 memory = {},
						 }) {
		const {C, db, env} = await this.load();
		// Insert user and update data
		const user = await db.users.insert({username, cpu, cpuAvailable, gcl, active});

		if (badgeColor) {
			await db.users.update({username: username}, {
				$set: {
					badge: {
						type  : 1,
						color1: badgeColor,
						color2: badgeColor,
						color3: badgeColor,
						param : 0,
						flip  : false
					}
				}
			});
		}

		await Promise.all([
							  env.set(env.keys.MEMORY + user._id, JSON.stringify(memory)),
							  db['users.code'].insert({user: user._id, branch: 'default', modules, activeWorld: true}),
						  ]);
		// Subscribe to console notificaiton and return emitter
		return new User(this.server, user).init();
	}

	/**
	 * Triggers reset of global for a user
	 */
	async triggerGlobalReset(user) {
		const {C, db, env} = await this.load();
		await db['users.code'].update({user: user._id, branch: 'default'}, {
			$set: {
				timestamp: new Date().getTime()
			}
		});
	}

	async updateEnvTerrain(db, env) {
		let walled = '';
		for (let i = 0; i < 2500; i += 1) {
			walled += '1';
		}
		const [rooms, terrain] = await Promise.all([
													   db.rooms.find(),
													   db['rooms.terrain'].find()
												   ]);
		rooms.forEach((room) => {
			if (room.status === 'out of borders') {
				_.find(terrain, {room: room._id}).terrain = walled;
			}
			const m = room._id.match(/(W|E)(\d+)(N|S)(\d+)/);
			const roomH = m[1] + (+m[2] + 1) + m[3] + m[4];
			const roomV = m[1] + m[2] + m[3] + (+m[4] + 1);
			if (!_.some(terrain, {room: roomH})) {
				terrain.push({room: roomH, terrain: walled});
			}
			if (!_.some(terrain, {room: roomV})) {
				terrain.push({room: roomV, terrain: walled});
			}
		});
		const compressed = await util.promisify(zlib.deflate)(JSON.stringify(terrain));
		await env.set(env.keys.TERRAIN_DATA, compressed.toString('base64'));
	}
}

module.exports = World;
