# -*- coding: utf-8 -*-

from socket import timeout as socket_timeout
import re
import logging
from threading import Semaphore
from datetime import datetime

DEVICE_U = DEVICE_P = 'cisco'
CISCO_NOPRIV = r'[\w-]+(\([\w-]+\))?> ?'
CISCO_PROMPT = [
    # IOS XE, IOS, IOS L2, NX-OS, NX-OS 9kv
    CISCO_NOPRIV,
    r'[\w-]+(\([\w-]+\))?# ?',
    # IOS XR
    r'RP\/0\/0\/CPU0:[\w-]+# ?',
    # RP/0/0/CPU0:ios_xrv-2#
]
LINUX_PROMPT = [
    r'%s@[\w\:~-]+\$ ?' % DEVICE_U
    # cisco@lxc-sshd-1$
]
USERNAME_PROMPT = [
    r'[uU]sername: ?',
    r'[lL]ogin: ?'
]
PASSWORD_PROMPT = [
    r'[pP]assword: ?',
    r'%s@[\w\.\'-]+ password: ?' % DEVICE_U
]
PROMPT = CISCO_PROMPT + LINUX_PROMPT


def interaction(sim, logname, dest_ip, transport, inlines, output_re, logic, timeout):
    '''interact with sim nodes via the LXC host (client).
    - sim is the current simulation
    - logname is the name of the node for the log filename 
      (if None then no log will be written
    - dest_ip is the IP of the sim node
    - transport is either 'ssh' or 'telnet'
    - inlines is a list of commands to be sent
    - output_re is a RE or list of REs we expect in the output
    - if logic is 'all', then all of the REs in output_re must match
      if logic is 'one', then at least one of the REs must match
    - timeout in seconds before the command interaction times out
    '''

    ok = False

    # transport and RE logic
    if transport not in ['ssh', 'telnet']:
        sim.log(logging.CRITICAL, 'unknown transport (not ssh or telnet)')
        return ok
    if logic not in ['all', 'one']:
        sim.log(logging.CRITICAL, 'unknown logic (not all or one)')
        return ok
    sim.log(logging.DEBUG, 'transport: %s, logic: %s', transport, logic)

    # open the SSH connection to the node
    interact = sim.sshOpen(timeout)
    # make sure only one at a time
    sim._semaphore.acquire()
    try:

        LXC_PROMPT = [r'%s@[\w-]+\$ ' % sim.simUser]

        interact.send('')
        interact.expect(LXC_PROMPT)
        if transport == 'ssh':
            interact.send('ssh %s@%s' % (DEVICE_U, dest_ip))
        else:
            interact.send('telnet %s' % dest_ip)
        interact.expect(USERNAME_PROMPT + PASSWORD_PROMPT)

        if transport == 'ssh':
            interact.send(DEVICE_P)
        if transport == 'telnet':
            if interact.last_match in USERNAME_PROMPT:
                interact.send(DEVICE_U)
                interact.expect(PASSWORD_PROMPT)
            if interact.last_match in PASSWORD_PROMPT:
                interact.send(DEVICE_P)
        interact.expect(PROMPT)

        # if we get an unprivileged prompt then
        # we're not enabled, need to enable first
        if interact.last_match == CISCO_NOPRIV:
            interact.send('enable')
            interact.expect(PASSWORD_PROMPT)
            interact.send(DEVICE_P)
            interact.expect(PROMPT)

        # at this point we SHOULD be logged in
        interact.send('')
        interact.expect(PROMPT)

        if not isinstance(inlines, list):
            inlines = list((inlines,))

        if not isinstance(output_re, list):
            output_re = list((output_re,))

        if logname is not None:
            filename = "%s-%s.log" % (datetime.utcnow().strftime('%Y%m%d%H%M%S'), logname)
            fh = open(filename, "w")
        else:
            fh = open(devnull, "w")

        for line in inlines:
            interact.send(line)
            fh.write('>>> %s\n' % line)
            interact.expect(PROMPT)
            fh.write('<<< %s\n' % interact.current_output_clean.split('\n')[0])
            for oline in interact.current_output_clean.split('\n')[1:]:
                fh.write('    %s\n' % oline)

        lines_found = 0
        for re_line in output_re:
            for oline in interact.current_output_clean.split('\n'):
                if re.search(re_line, oline):
                    lines_found += 1
                    break
            if lines_found > 0 and logic == 'one':
                break
        ok = lines_found == len(output_re) or lines_found > 0 and logic == 'one'

        # logout from the router
        interact.send('exit')
        interact.expect(LXC_PROMPT)
    except socket_timeout:
        sim.log(logging.CRITICAL, 'command interaction timed out')
        sim.sshClose()
        pass

    sim._semaphore.release()

    return ok
