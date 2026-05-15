from setuptools import setup, find_packages

setup(
    name="todlib",
    version="1.0.0",
    description="Libreria profesional para integracion con la red de mensajeria ToDus",
    author="Dev-FelixOfc",
    packages=find_packages(),
    install_requires=[
        "requests",
        "colorama"
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
)