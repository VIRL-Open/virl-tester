# -*- coding: utf-8 -*-
"Direct interact with the consoles of the sim, not via Mgmt-LXC."

import logging
import re

from telnetlib import Telnet
from socket import error as socket_error
from .prompts import CISCO_PROMPT, LINUX_PROMPT, USERNAME_PROMPT, PASSWORD_PROMPT, CISCO_NOPRIV

"""
asav.py:    plugin_name = 'ASAv'
base.py:    plugin_name = virl.plugins.Plugin.UNKNOWN
base.py:    plugin_name = 'generic'
coreos.py:    plugin_name = '~coreos'
csr1000v.py:    plugin_name = 'CSR1000v'
csr1000v.py:    plugin_name = 'ultra'
csr1000v.py:    plugin_name = 'CSR1000v_310'
docker.py:    plugin_name = 'docker'
iosv.py:    plugin_name = 'IOSv_unmanaged'
iosv.py:    plugin_name = 'vios_unmanaged'
iosv.py:    plugin_name = 'IOSv'
iosv.py:    plugin_name = 'vios'
iosv.py:    plugin_name = 'IOSvL2'
iosxrv.py:    plugin_name = 'IOS XRv'
iosxrv.py:    plugin_name = 'IOS XRv 9000'
iosxrv.py:    plugin_name = 'IOS XRv64'
iosxrv.py:    plugin_name = 'xrvr'
lxc.py:    plugin_name = 'lxc'
lxc.py:    plugin_name = 'lxc-tiny'
lxc.py:    plugin_name = 'lxc-sshd'
lxc_iol.py:    plugin_name = 'IOL'
lxc_iol.py:    plugin_name = 'IOL-L2'
lxc_iperf.py:    plugin_name = 'lxc-iperf'
lxc_mgmt.py:    plugin_name = 'mgmt-lxc'
lxc_ostinato.py:    plugin_name = 'lxc-ostinato-drone'
lxc_ostinato.py:#     plugin_name = 'lxc-ostinato'
lxc_routem.py:    plugin_name = 'lxc-routem'
nxosv.py:    plugin_name = 'NX-OSv'
nxosv.py:    plugin_name = 'titanium'
nxosv.py:    plugin_name = 'NX-OSv 9000'
server.py:    plugin_name = 'server'
server.py:    plugin_name = 'server_unmanaged'
server.py:    plugin_name = 'kali'
server.py:    plugin_name = 'security-onion'
server.py:    plugin_name = 'vPP'
server.py:    plugin_name = 'CoreOS'
server.py:    plugin_name = 'jumphost'
server.py:    plugin_name = 'Server'
staros.py:    plugin_name = 'StarOS'
vsrx.py:    plugin_name = 'vSRX'
vyatta.py:    plugin_name = 'Vyatta'
"""

# define the type, user/pass, initialization command and command to get for post-mortem
ASAV = ['ASAv', None, None, 'cisco', ['term pager 0'], ['show interface detail']]
CSR1KV = ['CSR1000v', None, None, 'cisco', ['term len 0'], ['show ip interface brief', ]]
IOSV = ['IOSv', None, None, 'cisco', ['term len 0'], ['show ip interface brief']]
IOSVL2 = ['IOSvL2', None, None, 'cisco', ['term len 0'], ['show interface status']]
IOSXRV = ['IOS XRv', 'cisco', 'cisco', '', ['term len 0 '], ['show ip interface brief', 'show ip route']]
IOSXRV9K = ['IOS XRv 9000', 'cisco', 'cisco', '', ['term len 0 '], ['show ip interface brief']]
NXOSV = ['NX-OSv', 'cisco', 'cisco', '', ['term len 0 '], ['show interface status']]
NXOSV9K = ['NX-OSv 9000', 'cisco', 'cisco', '', ['term len 0 '], ['show interface status']]
SERVER = ['server', 'cisco', 'cisco', '', [], ['ip route', 'ifconfig -a']]
COREOS = ['~coreos', 'cisco', 'cisco', '', [], ['ip route', 'ifconfig -a']]

DEVICES = {n[0]: n[1:] for n in [ASAV, CSR1KV, IOSV, IOSVL2, IOSXRV, IOSXRV9K, NXOSV, NXOSV9K, SERVER, COREOS]}

LastMatch = None

TIMEOUT = 5
ENCODING = 'utf-8'
CRLF = '\r\n'

# this needs to be byte-encoded for telnetlib...!?
PROMPT = [p.encode(ENCODING) for p in CISCO_PROMPT + LINUX_PROMPT]
UPRMPT = [p.encode(ENCODING) for p in USERNAME_PROMPT]
PPRMPT = [p.encode(ENCODING) for p in PASSWORD_PROMPT]
NOPRIV = [CISCO_NOPRIV.encode(ENCODING)]

""" we are assuming that the VMs which need a login are at the login prompt
    and have not been logged in at this point.
"""

def sendLine(telnet, prompt, line):
    """sends a line, then expects a prompt.
    the returned data from expect is:
    - p[0] the index of the given RE list that matched
    - p[1] the matched sre
    - p[2] the entire returned data (including the match)
    we then remove the prompt in the data.
    """
    global LastMatch

    if line is None:
        return None

    send_line = line.encode(ENCODING)
    # TODO: the following is a bit fishy:
    # b/c of adding the additional \n to the line?
    # works... needs testing if that would only be
    # added when needed?
    telnet.write(send_line + b'\n')
    if line != CRLF and not myMatch(UPRMPT + PPRMPT, LastMatch):
        telnet.expect([send_line], TIMEOUT)
    p = telnet.expect(prompt, TIMEOUT)
    if p[0] is -1:
        return None
    r = p[1].group(0)
    LastMatch = r
    return p[2].decode(ENCODING)


def myMatch(pattern_list, string):
    "Match the pattern."
    if string is None:
        return False
    for p in pattern_list:
        if re.match(p, string):
            return True
    return False


def postMortem(sim, sim_node_id, device_type, host, port):
    "Post mortem mode... interact direct with the console and log to file."
    st = DEVICES.get(device_type)
    if st is None:
        sim.log(logging.CRITICAL, 'postMortem: unknown device type [%s]' % device_type)
        return

    username, password, secret, init_cmd, show_cmd = st

    if sim is not None:
        fh = open("pm-%s-%s.log" % (sim.simId, sim_node_id), "w")
    else:
        import sys
        fh = sys.stdout

    try:
        tn = Telnet(host, port)
    except socket_error as e:
        fh.write(st)
        fh.write(str(e))
    else:
        sendLine(tn, UPRMPT + PROMPT, CRLF)

        if LastMatch is None:
            fh.write('can\'t get a response!')
            fh.close()
            tn.close()
            return

        # login prompt?
        if myMatch(UPRMPT, LastMatch):
            sendLine(tn, PPRMPT, username)
            sendLine(tn, PROMPT, password)

        # need to enable?
        if myMatch(NOPRIV, LastMatch):
            sendLine(tn, PPRMPT, 'enable')
            sendLine(tn, PROMPT, secret)

        # send the initialization (term length etc.)
        for line in init_cmd:
            sendLine(tn, PROMPT, line)

        # send the actual show commands
        for line in show_cmd:
            p = sendLine(tn, PROMPT, line)
            if p is not None:
                fh.write(p)

        # close session (should work across the board)
        sendLine(tn, [b'.*'], 'exit')
        tn.close()

    fh.close()


#postMortem(None, 'test', 'CSR1000v', '172.23.175.245', 17000)
#postMortem(None, 'test', 'IOS XRv', '172.23.175.245', 17009)
#postMortem(None, 'test', 'IOSv', '172.23.175.245', 17005)
#postMortem(None, 'test', 'server', '172.23.175.245', 17022)
#postMortem(None, 'test', 'NX-OSv 9000', '172.23.175.245', 17020)
#postMortem(None, 'test', 'NX-OSv', '172.23.175.245', 17012)
#postMortem(None, 'test', 'ASAv', '172.23.175.243', 17012)
