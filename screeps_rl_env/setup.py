import setuptools

setuptools.setup(
    name="Overmind-RL",
    version="0.0.0",
    author="Ben Bartlett",
    author_email="benbartlett@stanford.edu",
    description="Reinforcement learning for Overmind, the autonomous Screeps AI",
    license="MIT",
    url="https://github.com/bencbartlett/Overmind-RL",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ),
    install_requires=[
        "numpy",
        "scipy",
        "torch",
        "tensorflow",
        "gym",
        "ray",
        "tqdm",
        "zerorpc",
        "opencv-python-headless",
        "lz4",
        "setproctitle",
        "pydash"
    ],
)
