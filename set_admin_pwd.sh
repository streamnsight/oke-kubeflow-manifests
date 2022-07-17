#!/bin/bash

pip3 install bcrypt passlib -q

if [[ -z "${ADMIN_EMAIL}" ]]; then
    read -p "Admin Email: " ADMIN_EMAIL
fi
PASSWD_HASH=$(python3 -c 'from passlib.hash import bcrypt; import getpass; print(bcrypt.using(rounds=12, ident="2y").hash(getpass.getpass()))')
USERNAME=${ADMIN_EMAIL%@*}
sed -i "" -e "s|hash:.*|hash: $PASSWD_HASH|" -e "s|email:.*|email: $ADMIN_EMAIL|" -e "s|username:.*|username: ${USERNAME}|" ./upstream/common/dex/base/config-map.yaml

echo "user=${ADMIN_EMAIL}" > upstream/common/user-namespace/base/params.env
echo "profile-name=kubeflow-${ADMIN_EMAIL//[.@_]/-}" >> upstream/common/user-namespace/base/params.env

