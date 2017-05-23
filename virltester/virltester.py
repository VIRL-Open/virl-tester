# -*- coding: utf-8 -*-

from .loghandler import ColorHandler
from .command import interaction
from .sample_file import writeCommandSample
from .virl import VIRLSim

import logging
import argparse
import os
import textwrap
import threading
import yaml
import jinja2

from logging import DEBUG, INFO, WARN, ERROR, CRITICAL
from time import sleep
from io import TextIOWrapper

# default for wait time in seconds
# used for sim start and captures
MAXWAIT = 300

# 2 = WARNING
LOGDEFAULT = 2

# how long to wait for things when polling?
BUSYWAIT = 5


def initialSleep(virl, seq, action):
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
    seq = action['_seq']
    bg = action.get('background', False)
    bg_indicator = '*' if bg else ''
    virl.log(WARN, '(%s%d) filter: %s %s', bg_indicator, seq, name, intfc)

    initialSleep(virl, seq, action)
    capId = virl.createCapture(name, intfc, pcap, count)
    ok = False
    if capId is not None and virl.waitForCapture(capId, wait):
        ok = virl.downloadCapture(capId)
        virl.deleteCapture(capId)
    level = WARN if ok else ERROR
    virl.log(level, "(%d) capture succeeded: %s", action['_seq'], ok)
    action['success'] = ok


def doConvergeAction(virl, name, action, log_output):
    '''similar to command but will be called into a loop until it succeeds or
    max wait exceeded.
    essentially a command that will determine when the simulation has converged
    after it became active/reachable. e.g.
    - specific route entry in table
    - route table n-entries long
    - ping succeeds to IP 1.2.3.4
    - ...
    only after 
    '''

    converged = False
    waited = 0

    while True:
        doCommandAction(virl, name, action, False, converge=True)
        if action['success'] or waited > virl.simTimeout / 2:
            break
        virl.log(INFO, "waiting to converge... %d" % waited)
        sleep(virl.simPollInterval)
        waited += virl.simPollInterval
        action['sleep'] = 0


def doCommandAction(virl, name, action, log_output, converge=False):
    transport = action.get('transport', 'telnet')
    logic = action.get('logic', 'one')  # RE match: match once or all
    in_cmd = action.get('in')
    out_re = action.get('out')
    wait = action.get('wait', 30)

    # this stuff probably should all go into an Action class
    ok = False
    seq = action['_seq']
    bg = action.get('background', False)
    bg_indicator = '*' if bg else ''
    label = 'converge' if converge else 'command'
    virl.log(WARN, '(%s%d) %s: %s %s', bg_indicator, seq, label, name, in_cmd)
    initialSleep(virl, seq, action)

    # get the IP of the mgmt LXC for SSH
    address = virl.getMgmtIP(name)
    if address is not None:
        if log_output or action.get('log', False):
            logname = '-'.join((virl.simId, name))
        else:
            logname = None
        ok = interaction(virl, logname, address, transport,
                         in_cmd, out_re, logic, wait)
        if not converge:
            level = WARN if ok else ERROR
            label = 'SUCCEEDED' if ok else 'FAILED'
        else:
            level = WARN
            label = 'CONVERGED' if ok else 'WAITING'
        virl.log(level, "(%d) command %s", action['_seq'], label)
    action['success'] = ok


def doAction(func, threads, virl, name, action, *args):
    background = action.get('background', False)
    if background:
        new_args = [virl, name, action] + list(args)
        t = threading.Thread(target=func, args=new_args)
        t.daemon = True
        threads.append(t)
        t.start()
    else:
        func(virl, name, action, *args)


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
                        action['_seq'] = n
                        if action_type == 'filter':
                            doAction(doCaptureAction, threads, virl,
                                     name, action)
                            continue

                        if action_type == 'command':
                            log_output = sim.get('log', True)
                            doAction(doCommandAction, threads, virl,
                                     name, action, log_output)
                            continue

                        if action_type == 'converge':
                            log_output = sim.get('log', True)
                            doAction(doConvergeAction, threads, virl,
                                     name, action, log_output)
                            if not action['success']:
                                virl.log(CRITICAL, 'Sim did not converge! break action list')
                                break
                            continue

                        virl.log(CRITICAL, 'unknown action %s' % action_type)
            # wait for all action threads to stop
            if len(threads) > 0:
                virl.log(WARN, 'waiting for background actions to finish')
                for thread in threads:
                    thread.join()
            ok = True
        virl.stopSim(wait=True)
    if not ok:
        virl.log(CRITICAL, 'simulation %s failed' % virl.simId)
    return ok


def doAllSims(cmdfile, logger=None):

    # do we have a logger? If not, get the root logger
    if logger is None:
        logger = logging.getLogger()

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

    # if undefined make it one
    if cfg.get('parallel') is None:
        cfg['parallel'] = 1

    # start all sims
    try:
        for sim in cmdfile['sims']:
            if sim.get('skip', False):
                logger.warn('skipping sim %s', sim['topo'])
                continue

            # .virl files are relative to command file
            # prepend path of command file
            workdir = cmdfile.get('_workdir', '')
            topo = os.path.join(workdir, sim['topo'])
            wait = sim.get('wait', cfg_wait)
            virl = VIRLSim(cfg['host'], cfg['user'], cfg['password'],
                           topo, logger, timeout=wait)

            # for testing purposes
            #virl._sim_id = 'csr1kv-single-test-Uw32MT'
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
        logger.warning('waiting for background sims to end')
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


def loadCfg(fh, lvl=0):
    """load the YAML formatted configuration file specified by fh.
    Recursively include additional command files if the include
    key exist (list of files)

    includes:
    - command1.yml
    - command2.yml

    the 'includes' key is removed after recursive loading is done
    """
    if lvl > 10:
        raise yaml.scanner.ScannerError('recursion too deep')

    def useTemplate(fh):
        data = jinja2.Template(fh.read()).render(env=os.environ)
        return yaml.load(data)

    """"this works around a Python3 vs Python2 issue.
    A file handle is of type io.TextIOWrapper in Py3 and of
    type file in Py2.
    Sequence of testing is important :) if fh is a file then
    - in py2 it is False or True --> it is a file!
    - in py3 it is True or (not evaluated but it would cause an
      exception) --> it is a file

    Update: Well, if this is an included file then the var will
    be of type string and in Py3 it will check against 'file'
    which still causes an exception. Ah, crap.
    """

    # if isinstance(fh, TextIOWrapper) or isinstance(fh, file):
    # this misses unicode strings in python2
    if not isinstance(fh, str):
        data = useTemplate(fh)
    else:
        with open(fh, 'r') as f:
            data = useTemplate(f)
    if data.get('sims') is None:
        data['sims'] = list()
    for sim in data['sims']:
        sim['topo'] = os.path.expanduser(sim['topo'])
    includes = data.get('includes')
    if includes is not None:
        for include in includes:
            curdir = os.getcwd()
            try:
                path = os.path.dirname(include)
                basename = os.path.basename(include)
                if len(path) > 0:
                    os.chdir(path)
                subdata = loadCfg(basename, lvl + 1)
            except (IOError, OSError) as e:
                raise yaml.scanner.ScannerError("%s/%s: %s" % (
                      os.getcwd(), include, e.strerror))
            else:
                if subdata is not None:
                    for sim in subdata['sims']:
                        topo = sim['topo']
                        # if we are in a subdirectory, add the path
                        # but only if the topo name is not absolute
                        if not os.path.isabs(topo):
                            sim['topo'] = os.path.join(path, topo)
                        # make a note from where this was included
                        sim['_source'] = include
                        # append the sims to the parent sim list
                        data['sims'].append(sim)
            os.chdir(curdir)
        del data['includes']
    return data


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
    %(prog)s --example
    ''')

    parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('cmdfile', nargs='?', type=argparse.FileType('r'),
                       help="command file in YAML format")
    group.add_argument('--example', '-e', action='store_true',
                       help="create an example command file command-example.yml")

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
    if args.example:
        root_logger.warn('saving example commands to command-example.yml')
        ok = writeCommandSample()
    else:
        root_logger.info('loading command file')
        try:
            commands = loadCfg(args.cmdfile)
        except (yaml.scanner.ScannerError, yaml.parser.ParserError) as e:
            root_logger.critical('YAML: %s' % str(e).replace('\n', ''))
        else:
            # remember working directory
            commands['_workdir'] = os.path.dirname(args.cmdfile.name)
            # override command file loglevel
            loglevel = commands['config'].get('loglevel', LOGDEFAULT)
            if args.loglevel is not None:
                if loglevel != args.loglevel:
                    loglevel = args.loglevel
            root_logger.setLevel(logging.CRITICAL - loglevel * 10)
            ok = doAllSims(commands, root_logger)

    # shell return value
    return 0 if ok else -1
