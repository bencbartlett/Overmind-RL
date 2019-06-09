const _ = require('lodash');
const ScreepsEnvironment = require('./environment');
const TerrainMatrix = require('./serverMockup/src/terrainMatrix');


const env = new ScreepsEnvironment(0);

function testRoomIndexing(maxIndex) {
	// Test room indexing
	for (let index of _.range(maxIndex)) {
		const roomName = ScreepsEnvironment._roomFromIndex(index);
		const checkIndex = ScreepsEnvironment._indexFromRoom(roomName);
		console.log(`index: ${index}, roomName: ${roomName}`);
		console.log(`roomName: ${roomName}, index: ${checkIndex}`);
	}
}

async function testChangingRoomTerrain() {
	// Test changing room terrain once the server has been started
	roomName = ScreepsEnvironment._roomFromIndex(10);

	console.log(`Terrain for all rooms: `);
	console.log(await env.getAllRoomTerrain(false));

	await env.addRoom(roomName);

	console.log(`Terrain for room ${roomName}: `);
	console.log(await env.getRoomTerrain(roomName, false));

	console.log(await env.tick());

	console.log(`Setting terrain for room ${roomName}: `);
	const terrain = new TerrainMatrix();
	const walls = [[25, 25]];
	_.each(walls, ([x, y]) => terrain.set(x, y, 'wall'));
	await env.setRoomTerrain(roomName, terrain);

	console.log(`Terrain for room ${roomName}: `);
	console.log(await env.getRoomTerrain(roomName, false));

	console.log(`Setting terrain for room ${roomName}: `);
	const terrain2 = new TerrainMatrix();
	const walls2 = [[30, 30]];
	_.each(walls2, ([x, y]) => terrain2.set(x, y, 'wall'));
	await env.setRoomTerrain(roomName, terrain2);

	console.log(`Terrain for room ${roomName}: `);
	console.log(await env.getRoomTerrain(roomName, false));

	console.log(await env.tick());

	console.log(`Terrain for room ${roomName}: `);
	console.log(await env.getRoomTerrain(roomName, false));
}

async function testResettingRooms() {

	const room = ScreepsEnvironment._roomFromIndex(0);

	console.log('Pre-reset RoomObjects:', await env.getRoomObjects(room));

	console.log('Resetting room 0');
	await env.resetRoom(room);

	console.log('Post-reset same-tick RoomObjects:', await env.getRoomObjects(room));
	console.log(await env.tick());

	console.log('Post-reset next-tick RoomObjects:', await env.getRoomObjects(room));

}

async function testRoomObjects(numTicks = 10) {
	for (let tick in _.range(numTicks)) {
		console.log(await env.tick());
		const roomObjects = await env.getAllRoomObjects();
		console.log('All roomObjects:', JSON.stringify(roomObjects, null, '\t'));
	}
}

async function testMemoryWrite() {
	console.log(await env.setMemorySegment('Agent1', 70,
										   JSON.stringify({test: 5})));
	console.log(await env.tick());
	console.log(await env.setMemory('Agent1',
									JSON.stringify({test: 5})));
	console.log(await env.tick());
}

async function testAddingEnv() {
	if (!env.server.started) {
		throw new Error(`This should test adding env after server started`);
	}
	const roomName = await env.addEnv(3);
	console.log(`Terrain for room ${roomName}: `);
	console.log(await env.getRoomTerrain(roomName, false));
	console.log(`Room objects for ${roomName}: `, await env.getRoomObjects(roomName));
}

async function testEventLogs() {
	const room = ScreepsEnvironment._roomFromIndex(0);
	const creepName = `Agent1_${0}:${room}`;
	const healSelf = {[creepName]: [['heal', null]]};
	console.log(await env.sendCommands('Agent1', JSON.stringify(healSelf)));
	console.log(await env.tick());

	console.log(`Event log for ${room}:`, await env.getEventLog(room));
	console.log(`Clearing event log for ${room}`);
	await env.clearEventLog(room);
	console.log(`Event log for ${room}:`, await env.getEventLog(room));

	console.log(await env.tick());

}

async function run() {

	// testRoomIndexing(20);

	await env.addEnv(0);
	await env.addEnv(1);

	await env.resetTrainingEnvironment();

	for (let i in _.range(10)) {
		console.log(await env.tick());
	}

	// await testAddingEnv();
	await testRoomObjects(1);
	// await testResettingRooms();
	// await testMemoryWrite();
	await testEventLogs();
	// await testChangingRoomTerrain();

	console.log(await env.tick());

	env.stopServer();
}

run()
	.then(ret => {
		console.log(ret, 'done');
		process.exit();
	}).catch(console.error);

