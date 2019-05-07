const zerorpc = require('zerorpc');
const RemoteServer = require('./serverInterface');

process.argv.forEach(function (val, index, array) {
	console.log(index + ': ' + val);
});

const index = parseInt(process.argv[2], 10) || 0; // index of server

const server = new RemoteServer(index);

const rpcServer = new zerorpc.Server(
	{
		test: function (reply) {
			server.test().then(res => reply(null, res)).catch(err => reply(err));
		},

		initializeServer: function (reply) {
			server.initializeServer().then(res => reply(null, res)).catch(err => reply(err));
		},

		startServer: function (reply) {
			server.startServer().then(res => reply(null, res)).catch(err => reply(err));
		},

		tick: function (reply) {
			server.tick().then(res => reply(null, res)).catch(err => reply(err));
		},

		stopServer: function (reply) {
			server.stopServer().then(res => reply(null, res)).catch(err => reply(err));
		},

		exit: function (reply) {
			reply(null, 0);
			server.exit();
		},
	}
);

rpcServer.bind(`tcp://0.0.0.0:${server.commsPort}`);
