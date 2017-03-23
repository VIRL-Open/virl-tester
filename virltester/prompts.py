# -*- coding: utf-8 -*-

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
