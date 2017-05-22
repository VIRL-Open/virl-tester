#!/bin/bash

#set -x

doesImageExist () {
    virl_uwm_client --quiet --json docker-image-info | \
    jq '.["docker-images"][] | .name | contains("'$1'")' | \
    grep 'true'
}

image () {
    if ! [ $(doesImageExist docker-$1) ]; then
        virl_uwm_client docker-image-create --subtype docker --version $1 --image-url $1
    fi
}

! [ $(which jq) ] && sudo apt install -y jq
image httpd
image nginx

! [[ $(glance image-list) =~ "NX-OSv 9000" ]] && sudo salt-call -linfo state.sls virl.routervms.nxosv9k
! [[ $(glance image-list) =~ "NX-OSv  " ]] && sudo salt-call -linfo state.sls virl.routervms.nxosv
! [[ $(glance image-list) =~ "CSR1000v" ]] && sudo salt-call -linfo state.sls virl.routervms.csr1000v
! [[ $(glance image-list) =~ "ASAv" ]] && sudo salt-call -linfo state.sls virl.routervms.asav
! [[ $(glance image-list) =~ "coreos" ]] && sudo salt-call -linfo state.sls virl.routervms.coreos
! [[ $(glance image-list) =~ "IOS XRv" ]] && sudo salt-call -linfo state.sls virl.routervms.iosxrv
! [[ $(glance image-list) =~ "IOSv" ]] && sudo salt-call -linfo state.sls virl.routervms.iosv
! [[ $(glance image-list) =~ "IOSvL2" ]] && sudo salt-call -linfo state.sls virl.routervms.iosvl2
