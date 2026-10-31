from setuptools import setup, find_packages

setup(
    name="procure-agent",
    version="1.0.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "procure-agent = procure.cli:main",
            "worker-agent = procure.worker_cli:main",
        ],
    },
)
