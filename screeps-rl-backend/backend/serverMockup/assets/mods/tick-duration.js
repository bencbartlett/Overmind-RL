module.exports = function(config) {
	if (config.engine) {
		config.engine.mainLoopMinDuration = 1;
	}
};