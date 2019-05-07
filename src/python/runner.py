from multiprocessing import Pool
from subprocess import call


def run_server(server_index):
    print("Starting process " + str(server_index) + "...")
    call(["node", "../simulations/test.js", str(server_index), str(200)])


if __name__ == "__main__":
    num_processes = 1
    pool = Pool(num_processes)
    pool.map(run_server, range(num_processes))
