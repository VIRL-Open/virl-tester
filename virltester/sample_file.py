# -*- coding: utf-8 -*-

_sample_command_file = '''\
config:
  # the VIRL host
  host: 172.16.1.254
  # username and password
  user: guest
  password: guest
  # loglevel (0-4, 4=Debug)
  loglevel: 2
  # max parallel simulations
  parallel: 4
  # default wait time (spinup / actions)
  wait: 300


sims:
- topo: ~/Downloads/test-LtfPFU.virl
  # wait how long for sim to start (default: global wait)
  wait: 600
  # don't run this (default no)
  skip: yes
  # log all command actions (default yes)
  log: no
  # list of nodes (mandatory)
  nodes:
  - nx-osv9000-1:
    # list of actions per node (filter | command)
    - type: filter
      # should run in background (default no)?
      background: yes
      # maximum time for capture to finish (default: sim wait)
      wait: 300
      # amount of packets to capture
      count: 25
      # missing or empty filter: all packets
      pcap: icmp
      # mandatory interface
      intfc: Ethernet1/1
  - nx-osv9000-2:
    - type: filter
      # should run in background?
      background: yes
      # maximum time for capture to finish
      wait: 300
      # amount of packets to capture
      count: 25
      # missing or empty filter: all packets
      pcap: icmp
      # mandatory interface
      intfc: Ethernet1/1


  - nx-osv9000-1:
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
  - nx-osv9000-2:
    - type: command
      #background: yes
      sleep: 10
      wait: 5
      in: ping 10.0.0.5 count 50
      out: 0.00% packet loss
'''

def writeCommandSample():
    with open('command-sample.yml', 'w') as fh:
        fh.write(_sample_command_file)
