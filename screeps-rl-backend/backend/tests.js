const _ = require('lodash');
const ScreepsEnvironment = require('./environment');

const env = new ScreepsEnvironment(0);

function testRoomIndexing(maxIndex) {
    // Test room indexing
    for (let index of _.range(maxIndex)) {
        const roomName = ScreepsEnvironment._roomFromIndex(index);
        const checkIndex = ScreepsEnvironment._indexFromRoom(roomName);
        console.log(`index: ${index}, roomName: ${roomName}`);
        console.log(`roomName: ${roomName}, index: ${checkIndex}`)
    }
}

async function run() {

    // testRoomIndexing(20);

    env.addEnv(0);
    env.addEnv(1);

    await env.resetTrainingEnvironment();

    console.log(await env.tick());

    console.log("Terrain:", env.getAll);

    // console.log(await env.server.world.getRoomCreeps("E0S0"));
    console.log(await env.tick());

    console.log("All roomObjects:", await env.getAllRoomObjects());
    console.log(await env.tick());
    console.log(await env.tick());
    console.log(await env.tick());

    console.log("All roomObjects:", await env.getAllRoomObjects());
    console.log(await env.tick());


    console.log("All eventLogs:", await env.getAllEventLogs());
    console.log(await env.tick());

    console.log(await env.tick());

    console.log("Resetting room 0");
    await env.resetRoom(ScreepsEnvironment._roomFromIndex(0));
    console.log("All roomObjects:", await env.getAllRoomObjects());
    console.log(await env.tick());

    console.log("Resetting room 1");
    await env.resetRoom(ScreepsEnvironment._roomFromIndex(1));
    console.log("All roomObjects:", await env.getAllRoomObjects());
    console.log(await env.tick());



    console.log(await env.tick());


    console.log(await env.setMemorySegment('Agent1', 70,
        JSON.stringify({test: 5})));
    console.log(await env.tick());
    console.log(await env.tick());
    console.log(await env.setMemory('Agent1',
        JSON.stringify({test: 5})));
    console.log(await env.tick());
    console.log(await env.tick());
    env.stopServer();
}

run()
    .then(ret => {
        console.log(ret, 'done');
        process.exit();
    }).catch(console.error);

