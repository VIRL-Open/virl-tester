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
