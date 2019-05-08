const zerorpc = require('zerorpc');
const ScreepsEnvironment = require('./environment');

process.argv.forEach(function (val, index, array) {
	console.log(index + ': ' + val);
});

const index = parseInt(process.argv[2], 10) || 0; // index of server

const env = new ScreepsEnvironment(index);

const server = new zerorpc.Server(
	{
		test: function (reply) {
			env.test().then(res => reply(null, res)).catch(err => reply(err));
		},

		resetWorld: function(reply) {
			env.resetWorld().then(res => reply(null, res)).catch(err => reply(err));
		},

		resetTrainingEnvironment: function(reply) {
			env.resetTrainingEnvironment().then(res => reply(null, res)).catch(err => reply(err));
		},

		initializeServer: function (reply) {
			env.initializeServer().then(res => reply(null, res)).catch(err => reply(err));
		},

		startServer: function (reply) {
			env.startServer().then(res => reply(null, res)).catch(err => reply(err));
		},

		startBackend: function (reply) {
			env.startBackend().then(res => reply(null, res)).catch(err => reply(err));
		},

		tick: function (reply) {
			env.tick().then(res => reply(null, res)).catch(err => reply(err));
		},

		stopServer: function (reply) {
			env.stopServer().then(res => reply(null, res)).catch(err => reply(err));
		},

		exit: function (reply) {
			reply(null, 0);
			env.exit();
		},
	}
);

server.bind(`tcp://0.0.0.0:${env.commsPort}`);
