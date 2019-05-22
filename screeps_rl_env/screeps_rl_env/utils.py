import psutil

def kill_backend_processes(servers = (0, 1, 2), verbose = True):
    def on_terminate(proc):
        if verbose: print("Process {} terminated with exit code {}".format(proc, proc.returncode))

    look_ports = []
    for server in servers:
        look_ports.extend([21025 + 5 * server + 0, 21025 + 5 * server + 1, 21025 + 5 * server + 2])

    kill_pids = []
    for conn in psutil.net_connections():
        if (len(conn.laddr) > 0 and conn.laddr.port in look_ports) \
                or (len(conn.raddr) > 0 and conn.raddr.port in look_ports):
            kill_pids.append(conn.pid)

    print("Killing processes with pids {}".format(kill_pids))
    processes = [psutil.Process(pid = pid) for pid in kill_pids]

    for pid in kill_pids:
        process = psutil.Process(pid = pid)
        process.kill()

    dead, alive = psutil.wait_procs(processes, timeout = 3, callback = on_terminate)
    if verbose: print("Terminated processes: ", dead)
    if verbose: print("Remaining processes: ", alive)