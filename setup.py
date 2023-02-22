from setuptools import setup


setup(
    name='morgoth',
    version='0.1.0',
    license='MPL2',
    py_modules=[
        'morgoth',
    ],
    install_requires=[
        'boto3',
        'Click',
        'colorama',
        'pretty-bad-protocol',
        'requests',
    ],
    entry_points={
        'console_scripts': [
            'morgoth = morgoth.cli:cli',
        ],
    },
)
