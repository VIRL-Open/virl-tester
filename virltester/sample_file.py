# -*- coding: utf-8 -*-
"""produce a commented sample command file that has
(most) use cases covered."""

SAMPLE_COMMAND_FILE = '''\
config:
  # the VIRL host (using Jinja2 templating)
  host: {{ env["VIRL_HOST"] or "123.45.67.89" }}
  # username and password
  user: {{ env["VIRL_USER"] or "guest" }}
  password: {{ env["VIRL_PASS"] or "guest" }}
  # loglevel (0-4, 4=Debug)
  loglevel: 2
  # max parallel simulations
  parallel: 4
  # default wait time (spinup / actions)
  wait: 300


sims:
- topo: "~/Downloads/test-topology.virl"
  
  # wait how long for sim to start (default: global wait)
  wait: 600
  # don't run this (default no)
  skip: yes
  # log all command actions (default yes)
  log: no
  
  # list of nodes (mandatory)
  nodes:
  
  - name: nx-osv9000-1
    # list of actions per node (filter | command | converge)
    actions:
    - type: filter
      # should run in background (default no)?
      background: yes
      # maximum time for capture to finish (default: sim wait)
      wait: 300
      # amount of packets to capture
      count: 25
      # missing or empty filter: all packets
      bpf: icmp
      # mandatory interface
      intfc: Ethernet1/1
  
  - name: nx-osv9000-2
    actions:
    - type: filter
      # should run in background?
      background: yes
      # maximum time for capture to finish
      wait: 300
      # amount of packets to capture
      count: 25
      # missing or empty filter: all packets
      bpf: icmp
      # mandatory interface
      intfc: Ethernet1/1
  
  - name nx-osv9000-1
    actions:
    - type: command
      background: yes
      #sleep: 5
      wait: 5
      in:
      - term len 0
      - show version
      - ping 10.0.0.6 count 50
      out:
      - 50 packets received
      - 50/50
  
  - name: nx-osv9000-2
    actions:
    - type: command
      #background: yes
      sleep: 10
      wait: 5
      in: ping 10.0.0.5 count 50
      out: 0.00% packet loss
'''


def writeCommandSample():
    "Write the sample file."
    with open('command-example.yml', 'w') as fh:
        fh.write(SAMPLE_COMMAND_FILE)
    return True
