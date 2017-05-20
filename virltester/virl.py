# -*- coding: utf-8 -*-

import os
from datetime import datetime, timedelta
from time import sleep
from logging import DEBUG, INFO, WARN, ERROR, CRITICAL
from threading import Semaphore
import requests
import paramiko
from paramiko_expect import SSHClientInteraction
from .console import postMortem
from json import dumps


""" defines the simulation element """


class VIRLSim(object):
    '''holds configuration information of a VIRL simulation'''

    # will sleep for 'timeout / INTERVAL' when waiting for sim to start
    INTERVAL = 30

    def __init__(self, host, user, password, filename,
                 logger=None, timeout=300, port=19399):
        super(VIRLSim, self).__init__()
        self._host = host
        self._port = port
        self._filename = filename
        self._logger = logger
        self._timeout = timeout
        self._session = requests.Session()
        self._username = user
        self._password = password
        self._session.auth = (user, password)
        self._sim_id = None
        self._lxc_port = None
        self._no_start = False
        self._semaphore = Semaphore()
        self._ssh_client = None
        self._ssh_interact = None

    def _url(self, method='', roster=False):
        '''return the proper URL given the set vars and the
        method parameter.
        '''
        api = 'simengine'
        if roster:
            api = 'roster'
        return "http://{}:{}/{}/rest/{}".format(self._host, self._port, 
                                                api, method)

    def _request(self, verb, method, *args, **kwargs):
        url = self._url(method, roster=kwargs.pop('roster', False))
        r = self._session.request(verb, url, *args, **kwargs)
        if not r.ok:
            self.log(ERROR, 'VIRL API [%s]: %s',
                     r.status_code, r.json().get('cause'))
        return r

    def _post(self, method, *args, **kwargs):
        return self._request('POST', method, *args, **kwargs)

    def _get(self, method, *args, **kwargs):
        return self._request('GET', method, *args, **kwargs)

    def _delete(self, method, *args, **kwargs):
        return self._request('DELETE', method, *args, **kwargs)

    def log(self, level, *args, **kwargs):
        '''send the message in args to the logger with the given level.
        '''
        sim = self._sim_id if self._sim_id is not None else '<unknown>'
        newargs = list(args)
        newargs[0] = ': '.join((sim, args[0]))
        if self._logger is not None:
            return self._logger.log(level, *newargs, **kwargs)

    def isLogDebug(self):
        return self._logger.getEffectiveLevel() == DEBUG

    @property
    def simId(self):
        return self._sim_id

    @property
    def simHost(self):
        return self._host

    @property
    def simUser(self):
        return self._username

    @property
    def simPass(self):
        return self._password

    @property
    def sshInteract(self):
        if self._ssh_interact is not None:
            return self._ssh_interact
        return self.sshOpen()

    def startSim(self):
        '''This function will start a simulation using the provided .virl file
        '''
        sim_name = os.path.basename(os.path.splitext(self._filename)[0])
        self.log(WARN, 'Starting [%s]' % sim_name)

        # for debugging purposes. uses existing sim, does not start nor stop
        if self._no_start and len(self._sim_id) > 0:
            return True

        # Open .virl file and assign it to the variable
        ok = False
        try:
            with open(os.path.expanduser(self._filename), 'rb') as virl_file:
                # Parameter which will be passed to the server with the API call
                params = dict(file=sim_name)

                # Make an API call and assign the response information to the
                # variable
                r = self._post('launch', params=params, data=virl_file)

                # Check if call was successful, if true log it and return the value
                if r.status_code == 200:
                    self._sim_id = r.text
                    self.log(WARN, 'Simulation started.')
                ok = r.ok
        except IOError as e:
            self.log(CRITICAL, 'open file: %s', e)
        return ok

    def waitForSimStart(self):
        '''Returns True if the sim is started and all nodes are active/reachable
        waits for self._timeout (default 5min)
        '''
        active = False
        interval = self._timeout // self.INTERVAL
        if interval == 0:
            interval = self._timeout

        self.log(WARN, 'Waiting %ds to become active...', self._timeout)

        # for testing purposes
        #if self._no_start and len(self._sim_id) > 0:
        #   return True

        endtime = datetime.utcnow() + timedelta(seconds=self._timeout)
        while not active and endtime > datetime.utcnow():

            # Make an API call and assign the response information to the
            # variable
            r = self._get('nodes/%s' % self._sim_id)
            if not r.ok:
                return False

            # check if all nodes are active AND reachable
            nodes = r.json()[self._sim_id]
            active = True
            for node in nodes.values():
                if node['state'] == 'SHUTOFF':
                    continue
                if not (node['state'] == 'ACTIVE' and node['reachable']):
                    active = False
                    break

            # wait if not
            if not active:
                sleep(interval)

        # for testing purposes
        #active = False
        #nodes['csr1000v-1']['reachable'] = False

        if active:
            self.log(WARN, "Simulation is active.")
        else:
            self.log(ERROR, "Timeout... aborting!")

            # write status log file
            with open("status-%s.log" % self._sim_id, "w") as fh:
                fh.write(dumps(self.getStatus(), indent=2))

            for name, node in nodes.items():
                state = node['state']
                reachable = node['reachable']
                if not(state == 'ACTIVE' and reachable):
                    self.log(ERROR, "%s: %s, %s", name, state, reachable)

                    subtype, serial_port = self.getNodeDetail(name)
                    if serial_port is not None:
                        postMortem(self, name, subtype, self._host, serial_port)
                        self.log(ERROR, "error log written!")

        return active

    def stopSim(self):
        '''This function will stop the simulation
        '''
        self.log(WARN, 'Simulation stop...')

        # for debugging purposes
        if self._no_start and len(self._sim_id) > 0:
            return True

        # ensure SSH sessions are closed, if open
        self.sshClose()

        # Make an API call and assign the response information to the variable
        r = self._get('stop/%s' % self._sim_id)

        # Check if call was successful, if true log it and exit the application
        if r.status_code == 200:
            self.log(INFO, 'Simulation stop initiated.')

    def getNodeDetail(self, node):
        '''Get the node subtype and console port of the given node
        guest|csr1kv-single-test-9DYnbf|virl|csr1000v-1
        '''
        self.log(INFO, "Getting console port for [%s]...", node)
        r = self._get('', roster=True)
        if r.ok:
            for k, v in r.json().items():
                f = k.split('|')
                if len(f) > 1 and f[1] == self._sim_id and f[3] == node:
                    return (v.get('NodeSubtype'), v.get('PortConsole'))

    def getEvents(self):
        'Get the events associated with the sim'
        self.log(INFO, "Getting events...")
        r = self._get('events/%s' % self._sim_id)
        if r.ok:
            return r.json()

    def getStatus(self):
        'Get the status messages associated with the sim'
        self.log(INFO, "Getting status messages...")
        r = self._get('status/%s' % self._sim_id)
        if r.ok:
            return r.json()

    def getInterfaces(self, node):
        '''return the list of interfaces for the given node or
        None if not found.
        '''
        self.log(INFO, "Getting interfaces for [%s]...", node)
        params = dict(nodes=node)
        r = self._get('interfaces/%s' % self._sim_id, params=params)
        if r.ok:
            interfaces = r.json().get(self._sim_id).get(node)
            return interfaces
        self.log(ERROR, 'node not found: %s', node)
        return None

    def getInterfaceId(self, node, interface):
        '''get the interface index for the given interface name.
        '''
        self.log(INFO, "Getting ID from name [%s]...", interface)
        interfaces = self.getInterfaces(node)
        for key, intfc in interfaces.items():
            if intfc.get('name') == interface:
                self.log(INFO, "Found id: %s", key)
                return key

        self.log(ERROR, "Can't find specified interface %s", interface)
        return None

    def createCapture(self, node, interface, pcap_filter, count):
        '''Create a packet capture for the simulation using the given
        parameters in cfg
        '''
        self.log(WARN, "Starting packet capture...")

        # get interface based on name
        interface = self.getInterfaceId(node, interface)
        if interface is None:
            self.log(ERROR, "interface not found", interface)
            return None

        params = dict(node=node, interface=interface, count=count)
        params['pcap-filter'] = pcap_filter
        r = self._post('capture/%s' % self._sim_id, params=params)
        # did it work?
        if r.ok:
            capId = list(r.json().keys())[0]
            self.log(INFO, "Created packet capture (%s)", capId)
            return capId

    def deleteCapture(self, capId):
        '''delete the given packet capture with capId for the simulation
        '''
        self.log(INFO, "Deleting packet capture...")

        params = dict(capture=capId)
        r = self._delete('capture/%s' % self._sim_id, params=params)
        return r.ok

    def waitForCapture(self, capId, wait=None):
        '''Wait until the packet capture is done. check for the 'running'
        state according to the set wait time divided by INTERVAL divisor
        '''

        if wait is None:
            wait = self._timeout

        done = False
        interval = wait // self.INTERVAL
        if interval == 0:
            interval = wait

        self.log(INFO, 'Waiting %ds for capture [%s]', wait, capId)

        endtime = datetime.utcnow() + timedelta(seconds=wait)
        while not done and endtime > datetime.utcnow():

            # Make an API call and assign the response information to the
            # variable
            r = self._get('capture/%s' % self._sim_id)
            if not r.ok:
                return False

            # check if all nodes are active AND reachable
            captures = r.json()
            for cid, cval in captures.items():
                if cid == capId and not cval.get('running'):
                    done = True
                    break

            # wait if not
            if not done:
                sleep(interval)

        if done:
            self.log(WARN, "Capture has finished.")
        else:
            self.log(ERROR, "Timeout... aborting!")

        return done

    def downloadCapture(self, id):
        '''Download the finished capture and write it into a file
        '''
        content = 'application/vnd.tcpdump.pcap'
        params = dict(capture=id)
        headers = dict(accept=content)
        self.log(WARN, 'Downloading capture file...')

        # Make an API call and assign the response information to the
        # variable
        r = self._get('capture/%s' % self._sim_id,
                      params=params, headers=headers)
        if r.status_code == 200 and r.headers.get('content-type') == content:
            # "ContentDisposition":
            # "attachment; filename=V1_Ethernet1_1_2016-10-15-17-18-18.pcap
            filename = r.headers.get('Content-Disposition').split('=')[1]
            with open(filename, "wb") as fh:
                fh.write(r.content)
        else:
            self.log(ERROR, "problem... %s", r.headers)
            return False

        self.log(WARN, "Download finished.")
        return True

    def getMgmtIP(self, node):
        ''' return the management IP of the given Node name
        '''
        interfaces = self.getInterfaces(node)
        if interfaces is None:
            return None

        for key, intfc in interfaces.items():
            if key == 'management' and intfc.get('ip-address') is not None:
                address = intfc.get('ip-address').split('/')[0]
                self.log(INFO, "Found mgmt ip for %s: %s", node, address)
                return address

        self.log(ERROR, "Can't find Mgmt IP")
        return None

    def getLXCPort(self):
        ''' return the TCP port of the LXC host for the simulation
        the LXC can then be reached via the sim host on this port using
        SSH as the protocol.
        '''
        if self._lxc_port is not None:
            return self._lxc_port

        self._semaphore.acquire()
        interfaces = self.getInterfaces('~mgmt-lxc')
        if interfaces is not None:
            for key, intfc in interfaces.items():
                if key != 'management' and \
                   intfc.get('external-ip-address') is not None:
                    self._lxc_port = int(intfc.get('external-port'))
                    self.log(INFO, "Found LXC port: %s", self._lxc_port)
                    break
        if self._lxc_port is None:
            self.log(ERROR, "Can't find LXC port")
        self._semaphore.release()
        return self._lxc_port

    def sshOpen(self, timeout=5):
        if self._ssh_interact is not None:
            return self._ssh_interact

        self.log(WARN, 'Acquiring LXC SSH session')
        self._ssh_client = paramiko.SSHClient()
        paramiko.hostkeys.HostKeys(filename=os.devnull)
        # client.load_system_host_keys()
        self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._ssh_client.connect(hostname=self._host, username=self._username,
                                 password=self._password, port=self.getLXCPort())

        self._ssh_interact = SSHClientInteraction(self._ssh_client, timeout=timeout,
                                                  display=self.isLogDebug())
        return self._ssh_interact

    def sshClose(self):
        if self._ssh_interact is None:
            return
        self.log(WARN, 'Closing LXC SSH session')
        self._ssh_interact.close()
        self._ssh_client.close()
        self._ssh_interact = self._ssh_client = None

