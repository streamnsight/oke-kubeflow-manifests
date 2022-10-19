#!/bin/bash

read -rp "User Email: " EMAIL

if [[ -z $EMAIL ]]; then
    echo "Please provide an email."
    exit 1
fi

DEFAULT_USERNAME=$(echo "$EMAIL" | tr '._@' '---')
export DEFAULT_USERNAME

read -rp "Username/Namespace (defaults to '${DEFAULT_USERNAME}'): " USERNAME

if [[ -z ${USERNAME} ]]; then
    export USERNAME=$DEFAULT_USERNAME
fi

eval "echo \"$(cat ./oci/profile/user-profile.tmpl.yaml)\"" > "./oci/profile/${USERNAME}.Profile.yaml"

echo "Profile manifest created at './oci/profile/${USERNAME}.Profile.yaml'"

kubectl apply -f "oci/profile/${USERNAME}.Profile.yaml"
