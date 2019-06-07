(async function() {
	const _ = require('lodash');
	const fs = require('fs');
	const path = require('path');
	const {ScreepsServer, TerrainMatrix} = require('../src/main.js');

	// print process.argv
	process.argv.forEach(function(val, index, array) {
		console.log(index + ': ' + val);
	});

	const appDir = path.dirname(require.main.filename);
	console.log('appDir:' + appDir);

	const serverIndex = parseInt(process.argv[2], 10) || 0; // node /path/to/test.js 3 <- creates a third server instance
	const opts = {
		path   : path.resolve(appDir, '../../servers', `server${serverIndex}`),
		logdir : path.resolve(appDir, '../../servers', `server${serverIndex}`, 'logs'),
		port   : 21025 + serverIndex,
		modfile: path.resolve(appDir, '../serverMockup/assets/mods.json')
	};
	console.log('opts: ' + JSON.stringify(opts));

	const runTicks = parseInt(process.argv[3], 10) || 100;
	console.log('runTicks: ', runTicks);


	const server = new ScreepsServer(opts);

	try {
		// Initialize server
		await server.world.reset(); // reset world but add invaders and source keepers bots

		// Prepare the terrain for a new room
		const terrain = new TerrainMatrix();
		const walls = [[10, 10], [10, 40], [40, 10], [40, 40]];
		_.each(walls, ([x, y]) => terrain.set(x, y, 'wall'));

		// Create a new room with terrain and basic objects
		await server.world.addRoom('W0N1');
		await server.world.setTerrain('W0N1', terrain);
		await server.world.addRoomObject('W0N1', 'controller', 10, 10, {level: 0});
		await server.world.addRoomObject('W0N1', 'source', 10, 40, {
			energy             : 1000,
			energyCapacity     : 1000,
			ticksToRegeneration: 300
		});
		await server.world.addRoomObject('W0N1', 'mineral', 40, 40, {
			mineralType  : 'H',
			density      : 3,
			mineralAmount: 3000
		});

		// Add a bot in W0N1
		const overmindPath = path.resolve(__dirname, '../bots/overmind.js');
		const script = fs.readFileSync(overmindPath, 'utf8');
		const _script = `module.exports.loop = function() {
                console.log('Tick!',Game.time);
                const directions = [TOP, TOP_RIGHT, RIGHT, BOTTOM_RIGHT, BOTTOM, BOTTOM_LEFT, LEFT, TOP_LEFT];
                _.sample(Game.spawns).createCreep([MOVE]);
                _.each(Game.creeps, c => c.move(_.sample(directions)));
            };`;
		// console.log(script);
		const modules = {
			main: script,
		};
		const bot = await server.world.addBot({username: 'bot', room: 'W0N1', x: 25, y: 25, modules});

		// Print console logs every tick
		bot.on('console', (logs, results, userid, username) => {
			_.each(logs, line => console.log(`[console|${username}]`, line));
		});

		// Start server and run several ticks
		await server.start();
		for (let i = 0; i < runTicks; i += 1) {
			let start = new Date();
			console.log('\n[tick]', await server.world.gameTime);
			await server.tick();
			_.each(await bot.newNotifications, ({message}) => console.log('[notification]', message));
			// console.log('[memory]', await bot.memory);
			let end = new Date();
			let timeDiff = (end - start) / 1000;
			console.log(`Time elapsed: ${timeDiff}`);
		}


	} catch (err) {
		console.error(err);
	} finally {
		// Stop server and disconnect storage
		server.stop();
		process.exit(); // required as there is no way to properly shutdown storage :(
	}
}());
