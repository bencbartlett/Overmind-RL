const _ = require('lodash');
const fs = require('fs');
const path = require('path');
const {ScreepsServer, TerrainMatrix} = require('../serverMockup/src/main.js');

class RemoteServer {

	constructor(index) {
		this.index = index;
		this.serverPort = 21025 + index;
		this.commsPort = 22025 + index;

		// Start the server
		const appDir = path.dirname(require.main.filename);
		const opts = {
			path: path.resolve(appDir, '../../servers', `server${this.index}`),
			logdir: path.resolve(appDir, '../../servers', `server${this.index}`, 'logs'),
			port: this.serverPort,
			modfile: path.resolve(appDir, '../serverMockup/assets/mods.json')
		};

		console.log('opts: ' + JSON.stringify(opts));

		this.server = new ScreepsServer(opts);
	}

	async test() {
		console.log('poop');
		return this.serverPort;
	}

	async initializeServer() {

		// Initialize server
		await this.server.world.reset(); // reset world but add invaders and source keepers bots

		// Prepare the terrain for a new room
		const terrain = new TerrainMatrix();
		const walls = [[10, 10], [10, 40], [40, 10], [40, 40]];
		_.each(walls, ([x, y]) => terrain.set(x, y, 'wall'));

		// Create a new room with terrain and basic objects
		await this.server.world.addRoom('W0N1');
		await this.server.world.setTerrain('W0N1', terrain);
		await this.server.world.addRoomObject('W0N1', 'controller', 10, 10, {level: 0});
		await this.server.world.addRoomObject('W0N1', 'source', 10, 40, {
			energy: 1000,
			energyCapacity: 1000,
			ticksToRegeneration: 300
		});
		await this.server.world.addRoomObject('W0N1', 'mineral', 40, 40, {
			mineralType: 'H',
			density: 3,
			mineralAmount: 3000
		});

		// Add a bot in W0N1
		// const overmindPath = path.resolve(__dirname, '../bots/overmind.js');
		// const script = fs.readFileSync(overmindPath, 'utf8');

		const _script = `module.exports.loop = function() {
		        console.log('Tick!',Game.time);
		        const directions = [TOP, TOP_RIGHT, RIGHT, BOTTOM_RIGHT, BOTTOM, BOTTOM_LEFT, LEFT, TOP_LEFT];
		        _.sample(Game.spawns).createCreep([MOVE]);
		        _.each(Game.creeps, c => c.move(_.sample(directions)));
		    };`;

		// console.log(script);
		const modules = {
			main: _script,
		};
		const bot = await this.server.world.addBot({username: 'bot', room: 'W0N1', x: 25, y: 25, modules});

		// Print console logs every tick
		bot.on('console', (logs, results, userid, username) => {
			_.each(logs, line => console.log(`[console|${username}]`, line));
		});

	}

	async startServer() {
		await this.server.start();
	}

	async tick() {
		let start = new Date();
		await this.server.tick();
		let end = new Date();
		let timeDiff = (end - start) / 1000;
		console.log(`Time elapsed: ${timeDiff}`);
		return this.server.world.gameTime;
	}

	async stopServer() {
		this.server.stop();
	}

	exit() {
		process.exit();
	}

}

module.exports = RemoteServer;