# -*- coding: utf-8 -*-

import paramiko
from paramiko_expect import SSHClientInteraction
from socket import timeout as socket_timeout
import re
import logging
from threading import Semaphore
from os import devnull
from datetime import datetime

DEVICE_U = DEVICE_P = 'cisco'
PROMPT = [
    # IOS XE, IOS, IOS L2, NX-OS, NX-OS 9kv
    r'[\w-]+(\([\w-]+\))?[#>] ?', 
    # IOS XR
    r'RP\/0\/0\/CPU0:[\w-]+# ?'
    # RP/0/0/CPU0:ios_xrv-2#
]

# keep the client interaction alive
interact = client = None
semaphore = Semaphore()


def interaction(sim, logname, port, dest_ip, inlines, output_re, timeout):

    global client, interact

    semaphore.acquire()
    ok = False

    if interact is None:
        client = paramiko.SSHClient()
        paramiko.hostkeys.HostKeys(filename='/dev/null')
        # client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=sim.simHost, username=sim.simUser,
                       password=sim.simPass, port=port)

        interact = SSHClientInteraction(client, timeout=timeout,
                                        display=sim.isLogDebug())
    try:

        interact.send('')
        interact.expect([r'%s@[\w-]+\$ ' % sim.simUser])
        interact.send('telnet %s' % dest_ip)
        interact.expect([r'[uU]sername: ?', r'[lL]ogin: ?', r'[pP]assword: ?'])
        interact.send(DEVICE_U)
        interact.expect(PROMPT + [r'[pP]assword: ?'])

        # if we get a prompt right away then we're
        # not enabled, need to enable first
        if interact.last_match in PROMPT:
            interact.send('enable')
            interact.expect(r'[pP]assword: ?')
        interact.send(DEVICE_P)
        interact.expect(PROMPT)

        if not isinstance(inlines, list):
            inlines = list((inlines,))

        if not isinstance(output_re, list):
            output_re = list((output_re,))

        if logname is not None:
            filename = "%s-%s.log" % (datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z'), logname)
            fh = open(filename, "w")
        else:
            fh = open(devnull,"w")

        for line in inlines:
            interact.send(line)
            fh.write('>>> %s\n' % line)
            interact.expect(PROMPT)
            fh.write('<<< %s\n' % interact.current_output_clean.split('\n')[0])
            for oline in interact.current_output_clean.split('\n')[1:]:
                fh.write('    %s\n' % oline)

        for re_line in output_re:
            for oline in interact.current_output_clean.split('\n'):
                if re.search(re_line, oline):
                    ok = True
                    break
            if ok:
                break

        # logout from the router
        interact.send('exit')
        interact.expect([r'%s@[\w-]+\$ ' % sim.simUser])
    except socket_timeout:
        sim.log(logging.CRITICAL, 'command interaction timed out')
        interact.close()
        client.close()
        interact = client = None
        pass

    semaphore.release()

    return ok
