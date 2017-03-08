# -*- coding: utf-8 -*-

import paramiko
from paramiko_expect import SSHClientInteraction
from socket import timeout as socket_timeout
import re
import logging
from threading import Semaphore
from os import devnull
from datetime import datetime

transport = 'telnet'
dest_ip = '10.255.3.147'
logic = 'one'
#inlines = ['term len 0', 'show version']
inlines = ['no term pager', 'show version']
output_re = ['VLANs.*50']

DEVICE_U = DEVICE_P = 'cisco'

CISCO_NOPRIV = r'[\w-]+(\([\w-]+\))?> ?'
CISCO_PROMPT = [
    # ASA, IOS XE, IOS, IOS L2, NX-OS, NX-OS 9kv
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
LXC_PROMPT = [r'%s@[\w-]+\$ ' % 'guest']

PROMPT = CISCO_PROMPT + LINUX_PROMPT

client = paramiko.SSHClient()
paramiko.hostkeys.HostKeys(filename='/dev/null')
# client.load_system_host_keys()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname='172.23.175.92', username='guest',
               password='guest', port=10001)

interact = SSHClientInteraction(client, timeout=4, display=False)
DEVICE_P = DEVICE_U = 'cisco'

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

# if we get a unprivliged prompt then
# we're not enabled, need to enable first
if interact.last_match == CISCO_NOPRIV:
    interact.send('enable')
    interact.expect(PASSWORD_PROMPT)
    interact.send(DEVICE_P)
    interact.expect(PROMPT)


# at this point we SHOULD be logged in
interact.send('')
interact.expect(PROMPT)


for line in inlines:
    interact.send(line)
    # print('>>> %s\n' % line)
    interact.expect(PROMPT)
    print('#%s#%s#' % (interact.last_match, interact.current_output_clean))
    '''
    print('<<< %s\n' % interact.current_output_clean.split('\n')[0])
    for oline in interact.current_output_clean.split('\n')[1:]:
        print('    %s\n' % oline)
    '''

lines_found = 0
for re_line in output_re:
    for oline in interact.current_output_clean.split('\n'):
        if re.search(re_line, oline):
            lines_found += 1
            break
    if lines_found > 0 and logic == 'one':
        break
ok = lines_found == len(output_re) or lines_found > 0 and logic == 'one'
print("#%s#" % ok)

interact.send('exit')
interact.expect(LXC_PROMPT)

