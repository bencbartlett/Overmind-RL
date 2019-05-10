import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="Overmind-RL",
    version="0.0.0",
    author="Ben Bartlett",
    author_email="benbartlett@stanford.edu",
    description="Reinforcement learning for Overmind, the autonomous Screeps AI",
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bencbartlett/Overmind-RL",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ),
    install_requires=[
        "numpy",
        "scipy",
        "pytorch",
        "gym",
        "tqdm",
        "zerorpc"
    ],
)
