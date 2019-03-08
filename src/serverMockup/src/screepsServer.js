/* eslint no-console: "off", no-restricted-syntax: "off", global-require: "off" */

const cp = require('child_process');
const { EventEmitter } = require('events');
const fs = require('fs-extra-promise');
const _ = require('lodash');
const path = require('path');
const common = require('@screeps/common');
const driver = require('@screeps/driver');
const World = require('./world');

const ASSETS_PATH = path.join(__dirname, '..', 'assets');
const MOD_FILE = 'mods.json';
const DB_FILE = 'db.json';

class ScreepsServer extends EventEmitter {
    /*
        Constructor.
    */
    constructor(opts) {
        super();
        this.common = common;
        this.driver = driver;
        this.config = common.configManager.config;
        this.constants = this.config.common.constants;
        this.connected = false;
        this.lastAccessibleRoomsUpdate = -20;
        this.processes = {};
        this.world = new World(this);
        this.setOpts(opts);
    }

    /*
        Define server options and set defaults.
    */
    setOpts(opts = {}) {
        // Assign options
        this.opts = Object.assign({
            path:   path.resolve('server'),
            logdir: path.resolve('server', 'logs'),
            port:   21025,
        }, opts);
        // Define environment parameters
        process.env.MODFILE = this.opts.modfile;
        process.env.DRIVER_MODULE = '@screeps/driver';
        process.env.STORAGE_PORT = this.opts.port;
        return this;
    }

    /*
        Start storage process and connect driver.
    */
    async connect() {
        // Ensure directories exist
        await fs.mkdirAsync(this.opts.path).catch(() => {});
        await fs.mkdirAsync(this.opts.logdir).catch(() => {});
        // Copy assets into server directory
        await Promise.all([
            fs.copyFileAsync(path.join(ASSETS_PATH, DB_FILE), path.join(this.opts.path, DB_FILE)),
            fs.copyFileAsync(path.join(ASSETS_PATH, MOD_FILE), path.join(this.opts.path, MOD_FILE)),
        ]);
        // Start storage process
        this.emit('info', 'Starting storage process.');
        const library = path.resolve(path.dirname(require.resolve('@screeps/storage')), '../bin/start.js');
        const process = await this.startProcess('storage', library, {
            DB_PATH:      path.resolve(this.opts.path, DB_FILE),
            MODFILE:      path.resolve(this.opts.path, MOD_FILE),
            STORAGE_PORT: this.opts.port,
        });
        await new Promise((resolve, reject) => {
            const timeout = setTimeout(() => reject(new Error('Could not launch the storage process (timeout).')), 5000);
            process.on('message', (message) => {
                if (message === 'storageLaunched') {
                    clearTimeout(timeout);
                    resolve();
                }
            });
        });
        // Connect to storage process
        try {
            const oldLog = console.log;
            console.log = _.noop; // disable console
            await driver.connect('main');
            console.log = oldLog; // re-enable console
            this.usersQueue = await driver.queue.create('users', 'write');
            this.roomsQueue = await driver.queue.create('rooms', 'write');
            this.connected = true;
        } catch (err) {
            throw new Error(`Error connecting to driver: ${err.stack}`);
        }
        return this;
    }

    /*
        Run one tick.
    */
    async tick() {
        await driver.notifyTickStarted();
        const users = await driver.getAllUsers();
        await this.usersQueue.addMulti(_.map(users, user => user._id.toString()));
        await this.usersQueue.whenAllDone();
        const rooms = await driver.getAllRooms();
        await this.roomsQueue.addMulti(_.map(rooms, room => room._id.toString()));
        await this.roomsQueue.whenAllDone();
        await driver.commitDbBulk();
        await require('@screeps/engine/src/processor/global')();
        await driver.commitDbBulk();
        const gameTime = await driver.incrementGameTime();
        await driver.updateAccessibleRoomsList();
        await driver.notifyRoomsDone(gameTime);
        await driver.config.mainLoopCustomStage();
    }

    /*
        Start a child process with environment.
    */
    async startProcess(name, execPath, env) {
        const fd = await fs.openAsync(path.resolve(this.opts.logdir, `${name}.log`), 'a');
        this.processes[name] = cp.fork(path.resolve(execPath), { stdio: [0, fd, fd, 'ipc'], env });
        this.emit('info', `[${name}] process ${this.processes[name].pid} started`);
        this.processes[name].on('exit', async (code, signal) => {
            await fs.closeAsync(fd);
            if (code && code !== 0) {
                this.emit('error', `[${name}] process ${this.processes[name].pid} exited with code ${code}, restarting...`);
                this.startProcess(name, execPath, env);
            } else if (code === 0) {
                this.emit('info', `[${name}] process ${this.processes[name].pid} stopped`);
            } else {
                this.emit('info', `[${name}] process ${this.processes[name].pid} exited by signal ${signal}`);
            }
        });
        return this.processes[name];
    }

    /*
        Start processes and connect driver.
    */
    async start() {
        this.emit('info', `Server version ${require('screeps').version}`);
        if (!this.connected) {
            await this.connect();
        }
        this.emit('info', 'Starting engine processes.');
        this.startProcess('engine_runner', path.resolve(path.dirname(require.resolve('@screeps/engine')), 'runner.js'), {
            DRIVER_MODULE: '@screeps/driver',
            MODFILE:       path.resolve(this.opts.path, DB_FILE),
            STORAGE_PORT:  this.opts.port,
        });
        this.startProcess('engine_processor', path.resolve(path.dirname(require.resolve('@screeps/engine')), 'processor.js'), {
            DRIVER_MODULE: '@screeps/driver',
            MODFILE:       path.resolve(this.opts.path, DB_FILE),
            STORAGE_PORT:  this.opts.port,
        });
        return this;
    }

    /*
        Stop most processes (it is not perfect though as some remain).
    */
    stop() {
        _.each(this.processes, process => process.kill());
        return this;
    }
}

module.exports = ScreepsServer;
