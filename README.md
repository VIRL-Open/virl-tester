# README.md

this is the README file for *virltester*

to make it work with containers (like the mgmt LXC) you also do need to manually clone my fork of paramiko expect (see Installation section).

Lacks coherent Examples and better documentation in general. Some of them are
plain wrong (as the YAML has evolved over time :) ) and some are redundant /
misplaced etc.

The Examples/test.yml and the simple.yml in the baseline directory in Examples
*should* work. 

The `WORKDIR` directory should have a consistent set of files for a basic smoke test.

**It requires Python3.**

# Installation
- create a virtual environment `pip -p /opt/local/bin/python3.5 VENV`
- activate it `source VENV/bin/activate`
- install the library `pip install .` -or-
- install it editable `pip install -e .`
- add the paramiko-expect fork: `pip install git+https://github.com/rschmied/paramiko-expect.git` 

```
sudo apt install -y virtualenv
virtualenv venv
cd venv/
source bin/activate
https_proxy="http://proxy.esl.cisco.com:80" pip install git+https://github.com/rschmied/paramiko-expect.git
pip install git+http://gitlab.cisco.com/rschmied/virltester.git
```

# Using the Tool

```
$ virltester --help
usage: virltester [-h] [--sample] [--nocolor] [--loglevel {0,1,2,3,4}]
                  [cmdfile]

virltester uses a command file to start simulations, waits for them to
become active and then executes actions on given nodes of the running
simulations.

Configuration is parametrized by providing
- host: the hostname or IP of the VIRL host
- user and password: typically guest and guest
- loglevel: 0-4 (4=DEBUG), command line overrides command file
- parallel: how many simulation should be run in parallel?
- wait: default wait time for simulations to start

Simulations and nodes within a simulation can be specified as lists
to allow to fire up multiple simulations (also in parallel) and
execute actions on multiple nodes of a simulation (also in parallel).

Simulations parameters are
- topo: the topology file to use
- wait: the individual wait time for the sim to start
  (uses the global wait time if ommitted)
- nodes: a list of nodes with names and actions

A node is:
- a node name (like "iosv-1")
- a list of actions

Actions for a node can be
- filter: start a packet filter with given parameters (packet count,
  and pcap filter)
- command: executes commands on the node (via the LXC) and compares
  output against a set of regex strings. Both commands and expected
  result strings can be given in lists.

For both actions the following common parameter can be specified
- background: run the action as a thread in the background
- sleep: wait specified time before actions starts in seconds
- wait: maximum time to wait before giving up in seconds

positional arguments:
  cmdfile               command file in YAML format

optional arguments:
  -h, --help            show this help message and exit
  --sample, -s          create a sample command file command-sample.yml
  --nocolor, -n         don't use colors for logging
  --loglevel {0,1,2,3,4}, -l {0,1,2,3,4}
                        loglevel, 0-4 (default is 2)

Example:
virltester --loglevel 4 command.yml
virltester -l0 command2.yml
virltester --sample
$
```

Exit status is 0 when all tests were successful or -1 otherwise.

## Includes
Command files can include other command files. In this case it only includes the `config` section and then an additional `include` section instead of the `sims` sections:

```
config:
  host: 172.16.1.254
  user: guest
  password: guest

includes:
- subcommand1.yml
- subcommand2.yml
```

# Basic Smoke Test
The WORKDIR directory has a set of files which test all existing node types (reference platform VMs). It includes

- a topology with LXC-1 -- DuT -- LXC-2 for each node type (.yml and .virl)
- a test description for each node type which spins up the sim and, after it becomes active, pings LXC-2 from LXC-1 and vice versa

The test verifies that nodes come up fine and frames are forwarded. The `allnodes.yml` file does this for all node types (minus the XRv9000 as that one is currently broken).

## Loops

```bash
for i in $(seq 100); do { time virltester allnodes.yml ;}  >>main.log 2>&1 ; done
```


## Ideas
- implement a better action handler (e.g. list of actions mapped to functions)
- implement sim and action queueing (thread safety??)
- add start/stop action for nodes in sim
- add link up/down action for node interfaces
- add link conditioning action for node interfaces
- implement exception handling for API call failures
- implement negation of RE (e.g. 'not "100% ping loss"' string)
- don't start by default, only when action 'start' is given
- action 'wait to become active' or something
- node filter based on nodes (e.g. 'filter "stage-2"') for each command
- do not sim at end-action
- prefix where log files should be written (cmd-line switch)

## Done
- add getConsole for Sim / node
- in case of sim not going active/reachable, implement a console fallback to check what's going on on the node
