# -*- coding: utf-8 -*-
"Interact with devices using the existing LXC SSH session."

import socket
import re
import logging
from datetime import datetime
from os import devnull
from time import sleep

from .prompts import USERNAME_PROMPT, PASSWORD_PROMPT, CISCO_NOPRIV, PROMPT

"""
console=dict(device_type='cisco_ios_telnet',
             ip='172.23.175.245',
             port=17000,
             verbose=True,
             secret='cisco')
net_connect = netmiko.ConnectHandler(**console)
net_connect.find_prompt()
net_connect.enable()
r=net_connect.send_command('sh ip int brief')
print(r)
net_connect.disconnect()
"""


def interaction(sim, logname, dest_ip, transport, username, password, inlines, output_re, logic, timeout, converge=False):
    """interact with sim nodes via the LXC host (client).
    - sim is the current simulation
    - logname is the name of the node for the log filename
      (if None then no log will be written
    - dest_ip is the IP of the sim node
    - transport is either 'ssh' or 'telnet'
    - username and password (default cisco/cisco)
    - inlines is a list of commands to be sent
    - output_re is a RE or list of REs we expect in the output
    - if logic is 'all', then all of the REs in output_re must match
      if logic is 'one', then at least one of the REs must match
    - timeout in seconds before the command interaction times out
    - converge is True if this is to check whether sim converged
      in this case, failure is OK, no logging if timeout / fail
      converge does not create a log file.
    """

    RETRY_ATTEMPTS = 8
    RETRY_SLEEP = 120

    ok = False
    fh = None

    # transport and RE logic
    if transport not in ['ssh', 'telnet']:
        sim.log(logging.CRITICAL, 'unknown transport (not ssh or telnet)')
        return ok
    if logic not in ['all', 'one', '!all', '!one']:
        sim.log(logging.CRITICAL, 'unknown logic, valid: "[!]all, [!]one"')
        return ok
    negate = '!' in logic
    logic = logic.replace('!', '')
    sim.log(logging.DEBUG, 'transport: %s, negate: %s, logic: %s', transport, negate, logic)

    # open the SSH connection to the node
    interact = sim.sshOpen(timeout)
    if interact is None:
        return False

    # make sure only one at a time
    sim.lock()

    # get a logfile
    if logname is not None and not converge:
        filename = "%s-%s.log" % (datetime.utcnow().strftime('%Y%m%d%H%M%S'), logname)
        fh = open(filename, "w")
    else:
        fh = open(devnull, "w")

    # this is the LXC prompt we expect
    LXC_PROMPT = [r'%s@[\w-]+\$ ?' % sim.simUser]

    # we need to get a prompt from the mgmt LXC
    done = False
    attempts = RETRY_ATTEMPTS
    while not done:
        try:
            interact.send('')
            interact.expect(LXC_PROMPT)
        except socket.timeout as e:
            sim.log(logging.WARN, 'ATTENTION: LXC issue (%s, %s)' % attempts, e)
            done = attempts > 0
            attempts -= 1
            sleep(RETRY_SLEEP)
        except socket.error as e:
            sim.log(logging.CRITICAL, 'SSH error (%s)' % e)
            interact = sim.sshOpen(timeout)
            if interact is None:
                sim.unlock()
                fh.close()
                return False
        else:
            done = True

    # interact with the target sourced from LXC mgmt host
    sim.log(logging.INFO, 'got initial prompt')
    try:
        done = False
        attempts = RETRY_ATTEMPTS
        while not done:
            if transport == 'ssh':
                interact.send('ssh 2>&1 -v -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no %s@%s' % (username, dest_ip))
            else:
                interact.send('telnet %s' % dest_ip)
            interact.expect(USERNAME_PROMPT + PASSWORD_PROMPT + LXC_PROMPT)
            done = not interact.last_match in LXC_PROMPT
            # done = re.search(r'Connection refused', interact.current_output_clean) is None
            if not done:
                sim.log(logging.WARN, 'ATTENTION: [%s]' % interact.current_output_clean.replace('\n', '\\n'))
                sim.log(logging.WARN, 'ATTENTION: last match: [%s]' % interact.last_match)
                sim.log(logging.WARN, 'ATTENTION: connection issue (%s)' % attempts)
                if attempts == 0:
                    raise socket.timeout
                sim.sshClose()
                sleep(RETRY_SLEEP)
                interact = sim.sshOpen(timeout)
                interact.send('')
                interact.expect(LXC_PROMPT)
                attempts -= 1

        sim.log(logging.INFO, 'logged in to target')
        if transport == 'ssh':
            interact.send(password)
        if transport == 'telnet':
            if interact.last_match in USERNAME_PROMPT:
                interact.send(username)
                interact.expect(PASSWORD_PROMPT)
            if interact.last_match in PASSWORD_PROMPT:
                interact.send(password)
        interact.expect(PROMPT)

        # if we get an unprivileged prompt then
        # we're not enabled, need to enable first
        if interact.last_match == CISCO_NOPRIV:
            interact.send('enable')
            interact.expect(PASSWORD_PROMPT)
            interact.send(password)
            interact.expect(PROMPT)

        # at this point we SHOULD be logged in
        interact.send('')
        interact.expect(PROMPT)

        if not isinstance(inlines, list):
            inlines = list((inlines,))

        if not isinstance(output_re, list):
            output_re = list((output_re,))

        for line in inlines:
            #interact.send(re.escape(line))
            interact.send(line)
            fh.write('>>> %s\n' % line)
            # interact.expect(re.escape(line))
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
        # xor with negate is the result
        ok = negate != (lines_found == len(output_re) or lines_found > 0 and logic == 'one')

        # logout from the router
        interact.send('exit')
        interact.expect(LXC_PROMPT)

    except socket.timeout:
        if not converge:
            sim.log(logging.CRITICAL, 'command interaction timed out (%ds)' % timeout)
            sim.log(logging.CRITICAL, 'last match: [%s]' % interact.last_match)
            sim.sshClose()
            # write rest of output to file
            fh.write('\n\npost-exception:')
            fh.write('<<< %s\n' % interact.current_output_clean.split('\n')[0])
            for oline in interact.current_output_clean.split('\n')[1:]:
                fh.write('    %s\n' % oline)
            # input('[enter to continue]')
        else:
            sim.log(logging.DEBUG, 'waiting for convergence')

    fh.close()
    sim.unlock()

    return ok
