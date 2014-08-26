from setuptools import setup

setup(
    name='reql_cli',
    version='0.1.0',
    packages=['reqlcli'],
    scripts=['reqlcli/rql'],
    description='Run RethinkDB ReQL commands from the terminal',
    license='MIT',
    author='Josh Kuhn',
    author_email='deontologician@gmail.com',
    url='https://github.com/deontologician/reql_cli',
    keywords=['rethinkdb', 'reql', 'rql', 'cli', 'commandline'],
    install_requires = [
        'rethinkdb>=1.13',
        'pygments>=1.6',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
    ],
)
