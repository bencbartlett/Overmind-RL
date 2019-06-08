import platform

import psutil


def kill_backend_processes(server_index, verbose=True):
    def on_terminate(proc):
        if verbose: print("Process {} terminated with exit code {}".format(proc, proc.returncode))

    look_ports = [21025 + 5 * server_index + 0,
                  21025 + 5 * server_index + 1,
                  21025 + 5 * server_index + 2,
                  22025 + 5 * server_index]

    kill_pids = []
    for conn in psutil.net_connections():
        if (len(conn.laddr) > 0 and conn.laddr.port in look_ports) \
                or (len(conn.raddr) > 0 and conn.raddr.port in look_ports):
            kill_pids.append(conn.pid)

    print("Killing processes with pids {}".format(kill_pids))
    processes = [psutil.Process(pid=pid) for pid in kill_pids]

    for pid in kill_pids:
        process = psutil.Process(pid=pid)
        process.kill()

    dead, alive = psutil.wait_procs(processes, timeout=3, callback=on_terminate)
    if verbose: print("Terminated processes: ", dead)
    if verbose: print("Remaining processes: ", alive)


def running_on_laptop():
    return platform.node() == "tau"
