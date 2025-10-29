import os
import setuptools

setuptools.setup(
    name="ctb",
    version="1.0.0",
    description="Capture the Bug",
    packages=setuptools.find_packages("src"),
    package_dir = { "": "src" },
    install_requires=[
        "PyYAML==5.3.1",
        "requests==2.25.0",
        "termcolor==1.1.0"
    ]
)
