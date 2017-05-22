# README.md

this is the README file for *virltester*

> **Obsolete:** to make it work with containers (like the mgmt LXC) you also do need to manually clone my fork of paramiko expect (see Installation section).

Lacks coherent Examples and better documentation in general. Some of them are
plain wrong (as the YAML has evolved over time :) ) and some are redundant /
misplaced etc.

The Examples/test.yml and the simple.yml in the baseline directory in Examples
*should* work. 

The `WORKDIR` directory should have a consistent set of files for a basic smoke test.

**It runs Python2/3.**

# Installation
- create a virtual environment
- activate it
- clone repository (with proxy, if needed)

```
# Python 2.x:
sudo apt install -y virtualenv tmux
virtualenv venv
source venv/bin/activate

# Python 3.x:
sudo apt install -y pip3 tmux
pip -p /opt/local/bin/python3.5 venv
source venv/bin/activate
```

then install the package:

```
http_proxy="http://proxy-wsa.esl.cisco.com:80" \
git clone http://rschmied@gitlab.cisco.com/rschmied/virltester.git
```

- install the library `pip install .` -or-
- install it editable `pip install -e .`

-or-

```
http_proxy="http://proxy-wsa.esl.cisco.com:80" \
pip install git+http://gitlab.cisco.com/rschmied/virltester.git
```

**Obsolete Install Items**  

- add the paramiko-expect fork:

```
https_proxy="http://proxy-wsa.esl.cisco.com:80" \
pip install git+https://github.com/rschmied/paramiko-expect.git
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

## Incantations

See the `batch.sh` script that has a loop example plus some statistics. The below works too:

```bash
for i in $(seq 100); do { time virltester allnodes.yml ;}  >>main.log 2>&1 ; done
```

Using Jinja, env vars can be included into the YAML files for e.g. hosts, usernames and passwords...:


```bash
# in the YAML:
#   host: {{ env['VIRL_HOST'] or "localhost" }}
$ VIRL_HOST=172.23.175.243 virltester -l4 iosv-single-test.yml
```


## Ideas
- save start time in VIRL object and display a delta time when logging text
- implement a better action handler (e.g. list of actions mapped to functions)
- implement sim and action queueing (thread safety??)
- add start/stop action for nodes in sim
- add link up/down action for node interfaces
- add link conditioning action for node interfaces
- implement better exception handling for API call failures
- implement negation of RE (e.g. 'not "100% ping loss"' string)
- don't start by default, only when action 'start' is given
- action 'wait to become active' or something
- node filter based on node labels (e.g. 'filter "stage-2"') for each command
- 'do not stop sim at end'-action
- prefix where log files should be written (cmd-line switch)
- allow interaction with VIRL host node (via e.g. 172.16.1.254 or something that can be retrieved via roster... essentially, it's like a server node but with a different IP and username/password)
- wait until crypto signing check is done on all nodes / load is below threshold on host??

## Done
- add getConsole for Sim / node
- in case of sim not going active/reachable, implement a console fallback to check what's going on on the node
- use Jinja2 templates to allow env variables and other substitutions in the YAML like "{{ env['VIRL_HOST'] or "localhost" }}"
- wait until sim is truly stopped option
