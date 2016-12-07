# -*- coding: utf-8 -*-

import paramiko
from paramiko_expect import SSHClientInteraction
from socket import timeout as socket_timeout
import re
import logging
from os import devnull
from datetime import datetime

PROMPT = [
    # IOS XE, IOS, IOS L2, NX-OS, NX-OS 9kv
    r'[\w-]+(\([\w-]+\))?[#>] ?', 
    # IOS XR
    r'RP\/0\/0\/CPU0:[\w-]+# ?'
    # RP/0/0/CPU0:ios_xrv-2#
]


client = paramiko.SSHClient()
paramiko.hostkeys.HostKeys(filename='/dev/null')
# client.load_system_host_keys()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname='172.23.175.92', username='guest',
               password='guest', port=10002)

interact = SSHClientInteraction(client, timeout=5, display=True)

inlines = [ 'term len 0', 'sh version']
output_re = ''

interact.send('')
interact.expect([r'%s@[\w-]+\$ ' % 'guest'])
#interact.send('telnet %s' % '10.255.2.211')
interact.send('telnet %s' % '10.255.2.208')
interact.expect([r'[uU]sername: ?', r'[lL]ogin: ?', r'[pP]assword: ?'])
interact.send('cisco')
interact.expect(PROMPT + [r'Password: ?'])

# if we get a prompt right away then we're 
# not enabled, need to enable first
if interact.last_match in PROMPT:
    interact.send('enable')
    interact.expect(r'[pP]assword: ?')
interact.send('cisco')
interact.expect(PROMPT)

if not isinstance(inlines, list):
    inlines = list((inlines,))

if not isinstance(output_re, list):
    output_re = list((output_re,))

for line in inlines:
    interact.send(line)
    print('>>> %s\n' % line)
    interact.expect(PROMPT)
    print('<<< %s\n' % interact.current_output_clean.split('\n')[0])
    for oline in interact.current_output_clean.split('\n')[1:]:
        print('    %s\n' % oline)

for re_line in output_re:
    for oline in interact.current_output_clean.split('\n'):
        if re.search(re_line, oline):
            ok = True
            break
    if ok:
        break

# logout from the router
interact.send('exit')
interact.expect([r'%s@[\w-]+\$ ' % 'guest'])

interact.close()
client.close()

