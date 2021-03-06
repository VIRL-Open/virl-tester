# README.md

This is the README file for the *virltester* tool.

> **Note:** It should run with Python 2 and Python 3 but was mostly tested with Python 3.x.

## Installation

- create a virtual environment
- activate it
- clone repository (with proxy, if needed)
- install the library `pip install .` -or-
- install it editable `pip install -e .`

It's also possible to directly install from Git like here (set the `http_proxy` environment variable only when needed):

```plain
http_proxy="http://proxy.cisco.com:80" \
pip install git+http://github.com/virl-open/virl-tester.git
```

There is a Makefile in the directory to create a universal binary wheel that can be copied to target machines. For the Makefile to work, one has to also manually install the 'wheel' package.

## Using the Tool

```plain
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
- a node name (like "iosv-1") -or-
- an IP address ("172.16.1.254" is typically the VIRL host on FLAT),
- a list of actions associated with the node.

Actions for a node can be
- filter: start a packet filter with given parameters (packet count,
    and pcap berkely packet filter BPF)
- command: executes commands on the node (via the LXC) and compares
    output against a set of regex strings. Both commands and expected
    result strings can be given in lists.
- converge: like command. In this case it's a prerequisite before
    the remaining actions are started.

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

## Basic Smoke Tests

The Examples directory has a set of files to start with.

- `triangle.virl`: Used by the test YAML files.
- `iosv.yml`: Starts the triangle and does a few pings, generates log files
- `pcap.yml`: Waits for convergence, starts a pcap and pings on two nodes
- `config.yml`: Shows how to change the configuration of a device
- `virl-host.yml`: Interact with the VIRL host (or other nodes via IP address instead of node name)
- `include.yml`: Include other test files into a master test file

These basic examples can be used as a starting point for further, more complex testing.

## YAML Test Definition

### Syntax

The following tries to adhere to ABNF, see [here](https://en.wikipedia.org/wiki/Augmented_Backus%E2%80%93Naur_form) for the Wikipedia reference.

All the repetitions are essentially lists in the YAML whereas the rest is key / value pairs (dictionaries). See the Examples section how it should be rendered in YAML.

```plain
virltest = [config includes sims]
config = [host port username password loglevel wait parallel]
includes = *virltest; include the sims portion of other test files

host = string; hostname of the VIRL host to be used ('virl')
port = int; STD port number (19399)
username = string; for STD ('guest')
password = string; for STD ('guest')
loglevel = int; (2 = WARNING)
wait = int; maximum wait in [s] before it gives up (300)
parallel = int; how many sims in paralell (1)

sims = *(topo nodes [skip username password wait])
topo = string;  the .virl filename w/ optional path
nodes = name actions [username password]

skip = bool; should this be skipped?
username = string; per sim STD username (defaults to global username)
password = string; per sim STD password (defaults to global password)
wait = int; maximum wait in [s] before it gives up (defaults to global wait)

name = string; either valid nodename in topology or IP address
actions *(
  ("command"  in out [background log logic password transport username wait]) /
  ("converge") in out [background log logic password transport username wait]) /
  ("filter" intfc [background bpf count wait])
)

in = *1(string); RegExp
out = *1(string); RegExp, empty string is valid,
background = bool; should this action run in parallel?
log = bool; log this action in a separate logfile
logic = ["!"]("one" / "all") (default "one")
password = string; device passwod ("cisco")
transport = "telnet" / "ssh" (default "telnet")
username = string; device username ("cisco")
wait = int; how long to wait [s] for completion, (30)

intfc = string; Name of interface on the node to capture from (mandatory)
background = bool; should this action run in parallel?
bpf = string; BPF filter to apply ("", e.g. all packets)
count = int; Number of packets to capture (20)
wait = int; how long (seconds) to wait until capture stops (300)
```

### Examples

#### Minimal

The minimal input is the empty file which does... nothing:

empty.yml:

```yaml
# empty file
```

Output:

```plain
(venv) $ python vtest.py empty.yml
==> 2018-01-16 15:55:07 waiting for background sims to end
==> 2018-01-16 15:55:07 0 out of 0 succeeded
(venv) $
```

#### Basic IOSv Interaction

This uses Jinja2 to evaluate the host, username and password. If the environment variables are set, then those values are used. If not, then the provided defaults are used. If those lines would not be present, the system would fall back to the built-in defaults.

```yaml
config:
  host: {{ env['VIRL_HOST'] or "localhost" }}
  username: {{ env['VIRL_USER'] or "guest" }}
  password: {{ env['VIRL_PASS'] or "guest" }}

sims:
- topo: ../some/path/to/topology.virl
  - name: iosv-1
    actions:
    - type: command
      transport: telnet
      in:
      - term len 0
      - show version
      - conf t
      - hostname mychangedname
      - end
      - show run
      out:
      - ''
```

### Typical Config Section

```yaml
config:
  # the VIRL host
  host: {{ env["VIRL_HOST"] or "localhost" }}
  port: {{ env["VIRL_PORT"] or 19399 }}

  # username and password
  username: {{ env["VIRL_USER"] or "guest" }}
  password: {{ env["VIRL_PASS"] or "guest" }}
  # loglevel (0-4, 4=Debug)
  loglevel: 1
  # default wait time (spinup / actions)
  wait: 600
  # how many sims in parallel (resources!)
  #parallel: 1
```

### In/Out for Command/Converge

The 'in' list has strings which are sent to the device, line by line. After the last line has been sent, the 'out' list is used to match the output produced by the last command whether it matches any of the given regular expressions in 'out'.

The 'logic' parameter defines whether 'one' or 'all' of the 'out' lines have to match to mark the action as successful or not. It can be negated by prepending it with a '!'. E.g. '!one' means the action fails if one of these lines are present in any of the output lines and '!all' fails the action if all the given lines are found in the output.

### Convergence

The 'converge' action is similar to the regular 'command' action. But it is used to determine whether the simulation actually has converged (as opposed to all nodes being up and responding on the management interface).

For example, a topology is converged when on a particular node a specific route can be seen in the routing table... That route would only be present when the intermediate nodes are up and forwarding packets, BGP has been established between the peers and the prefix has been announces. So the command can check for that prefix in the routing table.

Only when the 'converge' action has succeeded, the subsequent actions in the action list are executed. For this reason, the 'converge' action should be the first action in the list of actions. However, this is not enforced. If the 'convert' action fails then the subsequent actions in the list will not be attempted.

### Inclusion of other test files

The 'includes' section allows to recursively include other test files into the main test file. Only the 'sims' list of the included files will be appended to the sims of the main test file.

This allows to define the configuration parameters in the main test file and the run the sims. Topology files are then read relative to the included test YAML files if no absolute path is given.

### Sample RegEx

```yaml
- name: lxc-1
  actions:
  - type: command
    transport: ssh
    in:
    - 'curl -Is http://10.0.0.5:80 | grep "200 OK")'
    out:
    - ^HTTP/1.1 200 OK$
```

This examples shows how an application (here: NGINX webserver) can be tested. The command connects to a LXC host in the topology, then runs curl to retrieve a web page from the container running NGINX and checks for a specific 'success' string in the 'out' RegEx. Note that there might be a 'sleep' required to allow for the processes to start.

### Incantations

The below starts the test 10 times and executes all sims in the 'allnodes.yml' test description, redirects every output to 'test.log'.

```bash
for i in $(seq 10); do
  { time virltester allnodes.yml ;} >>test.log 2>&1
done
```

Using Jinja, env vars can be included into the YAML files for e.g. hosts, usernames and passwords...:

```bash
# in the YAML:
#   host: {{ env['VIRL_HOST'] or "localhost" }}
$ VIRL_HOST=123.45.67.89 virltester -l4 iosv-single-test.yml
```

## Miscellaneous

### Ideas

- save start time in VIRL object and display a delta time when logging text
- implement a better action handler (e.g. list of actions mapped to functions)
- implement sim and action queueing (thread safety??)
- add start/stop action for nodes in sim
- add link up/down action for node interfaces
- add link conditioning action for node interfaces
- implement better exception handling for API call failures
- don't start by default, only when action 'start' is given
- node filter based on node labels (e.g. 'filter "stage-2"') for each command
- 'do not stop sim at end'-action
- prefix where log files should be written (cmd-line switch)
- Reset host, e.g. remove all running sims prior to starting tests

### Done

- allow interaction with VIRL host node (via e.g. 172.16.1.254 or something that can be retrieved via roster... essentially, it's like a server node but with a different IP and username/password)
- add getConsole for Sim / node
- in case of sim not going active/reachable, implement a console fallback to check what's going on on the node
- use Jinja2 templates to allow env variables and other substitutions in the YAML like "{{ env['VIRL_HOST'] or "localhost" }}"
- wait until sim has truly stopped option
- wait until sim has converged based on a given command / sequence of commands
  - action 'wait to become active' or something
  - wait until crypto signing check is done on all nodes / load is below threshold on host??

- implement negation of RE (e.g. 'not "100% ping loss"' string) (e.g. by providing "logic: !one" or "logic: !all" statements for action)
