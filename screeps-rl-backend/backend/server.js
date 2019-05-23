const _ = require('lodash');
const zerorpc = require('zerorpc');
const ScreepsEnvironment = require('./environment');

process.argv.forEach(function (val, index, array) {
    console.log(index + ': ' + val);
});

const index = parseInt(process.argv[2], 10) || 0; // index of server

const env = new ScreepsEnvironment(index);

const methods = [
    env.resetWorld,
    env.resetTrainingEnvironment,
    env.startBackend,
    env.startServer,
    env.stopServer,
    env.tick,
    env.getRoomTerrain,
    env.getRoomObjects,
    env.getEventLog,
    env.sendCommands,
    env.setMemory,
    env.setMemorySegment,
    // env.exit
];

let serverMethods = _.zipObject(
    _.map(methods, method => method.name),
    _.map(methods, method => (
        function (...args) {
            const _args = args.slice(0, -1);
            const reply = _.last(args);
            env[method.name](..._args)
                .then(res => reply(null, res))
                .catch(err => reply(err));
        }
    ))
);
serverMethods.exit = function (reply) {
    reply(null, 0);
    env.exit();
};


const server = new zerorpc.Server(serverMethods);

try {
    server.bind(`tcp://0.0.0.0:${env.commsPort}`);
} catch (e) {
    console.log(e);
    console.log("Exiting server!");
    process.exit();
}
