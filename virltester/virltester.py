# -*- coding: utf-8 -*-

from .loghandler import ColorHandler
from .command import interaction
from .sample_file import writeCommandSample
from .virl import VIRLSim

import logging
from logging import DEBUG, INFO, WARN, ERROR, CRITICAL
import argparse
import textwrap
import threading
import yaml
from time import sleep

# default for wait time in seconds
# used for sim start and captures
MAXWAIT = 300

# 2 = WARNING
LOGDEFAULT = 2

# how long to wait for things when polling?
BUSYWAIT = 5


def initialSleep(virl, seq, name, action):
    sleeptimer = action.get('sleep', 0)
    if sleeptimer > 0:
        virl.log(WARN, "(%d) initial sleep %ss", seq, sleeptimer)
        sleep(sleeptimer)
        virl.log(WARN, "(%d) initial sleep done", seq)


def doCaptureAction(virl, name, action):
    intfc = action['intfc']
    count = action.get('count', 20)
    pcap = action.get('pcap', '')
    wait = action.get('wait', None)

    # this stuff probably should all go into an Action class
    seq = action['seq']
    bg = action.get('background', False)
    bg_indicator = '*' if bg else ''
    virl.log(WARN, '(%s%d) filter: %s %s', bg_indicator, seq, name, intfc)

    initialSleep(virl, seq, __name__, action)
    capId = virl.createCapture(name, intfc, pcap, count)
    ok = False
    if capId is not None and virl.waitForCapture(capId, wait):
        ok = virl.downloadCapture(capId)
        virl.deleteCapture(capId)
    virl.log(WARN, "(%d) capture succeeded: %s", action['seq'], ok)
    action['success'] = ok


def doCommandAction(virl, name, action, log_output):
    in_cmd = action.get('in')
    out_re = action.get('out')
    wait = action.get('wait', 5)

    # this stuff probably should all go into an Action class
    seq = action['seq']
    bg = action.get('background', False)
    bg_indicator = '*' if bg else ''
    virl.log(WARN, '(%s%d) command: %s %s', bg_indicator, seq, name, in_cmd)
    initialSleep(virl, seq, __name__, action)

    port = virl.getLXCPort()
    address = virl.getMgmtIP(name)
    ok = False
    if log_output or action.get('log', False):
        logname = '-'.join((virl.simId, name))
    else:
        logname = None
    if port is not None:
        ok = interaction(virl, logname, port, address, in_cmd, out_re, wait)
    virl.log(WARN, "(%d) command succeeded: %s", action['seq'], ok)
    action['success'] = ok


#def doAction(func, threads, virl, name, action, log_output):
def doAction(func, threads, virl, name, action, *args):
    if not action.get('background', False):
        func(virl, name, action, *args)
    else:
        t = threading.Thread(target=func, args=(virl, name, action, args))
        t.daemon = True
        threads.append(t)
        t.start()


def doSim(virl, sim):

    ok = False
    threads = list()
    n = 0

    if virl.startSim():
        if virl.waitForSimStart():
            for node in sim.get('nodes', list()):
                for name, actions in node.items():
                    for action in actions:
                        n += 1
                        action_type = action.get('type', '<not set>')
                        action['seq'] = n
                        if action_type == 'filter':
                            doAction(doCaptureAction, threads, virl, 
                                     name, action)
                            continue

                        if action_type == 'command':
                            log_output = sim.get('log', True)
                            doAction(doCommandAction, threads, virl,
                                     name, action, log_output)
                            continue

                        virl.log(CRITICAL, 'unknown action %s' % action_type)
            # wait for all action threads to stop
            if len(threads) > 0:
                virl.log(WARN, 'waiting for backround tasks to finish')
                for thread in threads:
                    thread.join()
            ok = True
        virl.stopSim()
    if not ok:
        virl.log(CRITICAL, 'simulation %s failed' % virl.simId)
    return ok


def doAllSims(cmdfile, args, logger):

    cfg = cmdfile['config']
    cfg_wait = cfg.get('wait', MAXWAIT)

    # store threads and sims in this list
    sims = list()

    def activeSims():
        active = 0
        for sim in sims:
            if sim['thread'].isAlive():
                active += 1
        return active

    # start all sims
    try:
        for sim in cmdfile['sims']:
            if sim.get('skip', False):
                logger.warn('skipping sim %s', sim['topo'])
                continue
            wait = sim.get('wait', cfg_wait)
            virl = VIRLSim(cfg['host'], cfg['user'], cfg['password'],
                           sim['topo'], logger, timeout=wait)
            # virl._sim_id = '8node-iosxrv-NV0k8K'
            # virl._no_start = True
            #virl._sim_id = 'iosv-iosvl2-r4J3hY'
            #virl._no_start = True
            
            logger.warn('new thread %s', sim['topo'])
            t = threading.Thread(target=doSim, args=(virl, sim))
            t.daemon = True
            t.start()
            sims.append(dict(thread=t, virl=virl))
            if activeSims() == cfg.get('parallel'):
                busy = True
                while busy:
                    if activeSims() < cfg.get('parallel'):
                        busy = False
                        break
                    sleep(BUSYWAIT)
            # need to wait a bit to stagger sim starts
            sleep(BUSYWAIT)

        # wait for all sims to finish
        busy = activeSims() > 0
        while busy:
            sleep(BUSYWAIT)
            current = activeSims()
            logger.debug('waiting for %d sim(s) to end', current)
            busy = activeSims() > 0
    except KeyboardInterrupt:
        pass
    finally:
        # make sure to stop all started sims which are still active
        for sim in sims:
            if sim['thread'].isAlive() and sim['virl'].simId is not None:
                sim['virl'].stopSim()

    total = success = 0
    for sim in cmdfile['sims']:
        if sim.get('skip', False):
            continue
        for node in sim['nodes']:
            for actions in node.values():
                for action in actions:
                    total += 1
                    if action.get('success', False):
                        success += 1
    logger.warn('%d out of %d succeeded' % (success, total))

    return total == success


def main():

    description = textwrap.dedent('''\
    %(prog)s uses a command file to start simulations, waits for them to
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
    ''')

    epilog = textwrap.dedent('''\
    Example:
    %(prog)s --loglevel 4 command.yml
    %(prog)s -l0 command2.yml
    %(prog)s --sample
    ''')

    parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('cmdfile', nargs='?', type=argparse.FileType('r'),
                       help="command file in YAML format")
    group.add_argument('--sample', '-s', action='store_true',
                       help="create a sample command file command-sample.yml")

    parser.add_argument('--nocolor', '-n', action='store_true',
                        help="don't use colors for logging")
    parser.add_argument('--loglevel', '-l', type=int, choices=range(0, 5),
                        help="loglevel, 0-4 (default is %d)" % LOGDEFAULT)
    args = parser.parse_args()

    # setup logging
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.CRITICAL - LOGDEFAULT * 10)
    handler = ColorHandler(colored=(not args.nocolor))
    if args.nocolor:
        formatter = logging.Formatter("==> %(asctime)s %(levelname)-8s %(message)s", datefmt='%Y-%m-%d %H:%M:%S')
    else:
        formatter = logging.Formatter("==> %(asctime)s %(message)s", datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # run in config file mode
    ok = False
    if args.sample:
        root_logger.warn('saving sample commands to command-sample.yml')
        ok = writeCommandSample()
    else:
        root_logger.info('loading command file')
        try:
            commands = yaml.load(args.cmdfile)
        except (yaml.scanner.ScannerError, yaml.parser.ParserError) as e:
            root_logger.critical('YAML: %s' % str(e).replace('\n', ''))
        else:
            # override command file loglevel
            loglevel = commands['config'].get('loglevel', LOGDEFAULT)
            if args.loglevel is not None:
                if loglevel != args.loglevel:
                    loglevel = args.loglevel
            root_logger.setLevel(logging.CRITICAL - loglevel * 10)
            ok = doAllSims(commands, args, root_logger)

    # shell return value
    return 0 if ok else -1
