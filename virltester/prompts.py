# -*- coding: utf-8 -*-
"Define prompts for various devices we expect to see in sims."

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
    r'\w+@[\w\:~-]+\$ ?'
    # cisco@lxc-sshd-1$
]
USERNAME_PROMPT = [
    r'[uU]sername: ?',
    r'[lL]ogin: ?'
]
PASSWORD_PROMPT = [
    r'[pP]assword: ?',
    r'\w+@[\w\.\'-]+ password: ?'
]
PROMPT = CISCO_PROMPT + LINUX_PROMPT
