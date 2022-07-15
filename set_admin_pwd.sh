#!/bin/bash

pushd upstream/common/dex/base/ || exit 1

pip3 install bcrypt passlib -q

read -p "Admin Email: " EMAIL
PASSWD_HASH=$(python3 -c 'from passlib.hash import bcrypt; import getpass; print(bcrypt.using(rounds=12, ident="2y").hash(getpass.getpass()))')
cp config-map.yaml config-map.yaml.DEFAULT
USERNAME=${EMAIL%@*}
sed -i "" -e "s|hash:.*|hash: $PASSWD_HASH|" -e "s|email:.*|email: $EMAIL|" -e "s|username:.*|username: ${USERNAME}|" config-map.yaml
popd || exit 1
echo "user=${EMAIL}" > upstream/common/user-namespace/base/params.env
echo "profile-name=kubeflow-${EMAIL//[.@_]/-}" >> upstream/common/user-namespace/base/params.env

