#!/bin/bash
# set -x

. ./kubeflow_version.env

get_upstream () {
    CURRENT_DIR=$(pwd)
    UPSTREAM_FOLDER="${CURRENT_DIR}/upstream"
    echo -e "KubeFlow version ${KUBEFLOW_RELEASE_VERSION} installation checks.\n"
    # if folder exists
    if [ -d "$UPSTREAM_FOLDER" ]
    then
        echo "./upstream folder found"
        # Check the tag matches the release
        pushd "$UPSTREAM_FOLDER" > /dev/null || exit 1
        TAG=$(git describe --tags)
        echo "Upstream for version $TAG found"
        popd > /dev/null || exit 1
        # If not, clean up and clone
        if [[ "${TAG}" != "${KUBEFLOW_RELEASE_VERSION}" ]]; then
            echo "Version mismatch"
            rm -rf upstream;
        fi
    fi

    # upstream was cleared if there was a version mismatch, so if now the folder is not found, new version needs fetching
    if [ ! -d "$UPSTREAM_FOLDER" ]
    then
        echo "Fetching version ${KUBEFLOW_RELEASE_VERSION} ..."
        git clone -c advice.detachedHead=false --branch ${KUBEFLOW_RELEASE_VERSION} \
            https://github.com/kubeflow/manifests.git --single-branch upstream;
    fi
}

validate_kubectl () {
    # Validate kubectl is installed
    if ! command -v kubectl &>/dev/null
    then
        echo "kubectl not found" && exit 1
    fi
}

validate_cluster_version () {
    # Validate Kubernetes cluster version compatibility
    KUBERNETES_SERVER_VERSION=$(kubectl version --short 2>&1 | grep "Server" | awk -F":" '{print $2}' | tr -d 'v ')
    KUBERNETES_SERVER_VERSION_MAJOR=$(echo "${KUBERNETES_SERVER_VERSION}" | awk -F"." '{print $1}')
    KUBERNETES_SERVER_VERSION_MINOR=$(echo "${KUBERNETES_SERVER_VERSION}" | awk -F"." '{print $2}')

    echo "Kubernetes Server version: v${KUBERNETES_SERVER_VERSION}"

    if [[ ( ${KUBERNETES_SERVER_VERSION_MAJOR} -lt ${KUBEFLOW_MIN_K8S_VERSION_MAJOR} \
        || ${KUBERNETES_SERVER_VERSION_MINOR} -lt ${KUBEFLOW_MIN_K8S_VERSION_MINOR} ) \
        || ( ${KUBERNETES_SERVER_VERSION_MAJOR} -gt ${KUBEFLOW_MAX_K8S_VERSION_MAJOR} \
        || ${KUBERNETES_SERVER_VERSION_MINOR} -gt ${KUBEFLOW_MAX_K8S_VERSION_MINOR} ) \
        ]]
    then
        echo "Kubernetes version is not compatible: KubeFlow ${KUBEFLOW_RELEASE_VERSION} \
    requires Kubernetes version v${KUBEFLOW_MIN_K8S_VERSION_MAJOR}.${KUBEFLOW_MIN_K8S_VERSION_MINOR} to \
    ${KUBEFLOW_MAX_K8S_VERSION_MAJOR}.${KUBEFLOW_MAX_K8S_VERSION_MINOR}"
        exit 1
    fi
}

validate_kustomize () {
    # validate kustomize is installed
    if ! command -v kustomize &>/dev/null
    then
        echo "kustomize not found" && exit 1
    fi

    KUSTOMIZE_VERSION=$(kustomize version --short | awk -F" " '{print $1}' | awk -F"v" '{print $2}')
    KUSTOMIZE_VERSION_MAJOR=$(echo "${KUSTOMIZE_VERSION}" | awk -F"." '{print $1}')
    KUSTOMIZE_VERSION_MINOR=$(echo "${KUSTOMIZE_VERSION}" | awk -F"." '{print $2}')
    if [[ ${KUSTOMIZE_VERSION_MAJOR} -lt 3 || ${KUSTOMIZE_VERSION_MINOR} -lt 6 ]]
    then
        echo "kustomize v3.6 or higher is required"
        exit 1
    fi
    echo "Using kustomize v${KUSTOMIZE_VERSION}"
}

ENV_FILE="kubeflow.test3.env"
ENV_FILE_TEMPLATE="kubeflow.tmpl.env"

if [[ ! -f "${ENV_FILE}" ]]
then 
    cp kubeflow.tmpl.env ${ENV_FILE}
fi

ALL_VARIABLES=$(cat "${ENV_FILE_TEMPLATE}" | grep -E '^[^#]' | awk -F"=" '{print $1}')
# unset variables that may have been set in the global environment
for var in ${ALL_VARIABLES[@]}
do
    unset "${var}"
done

# source from the file
source "${ENV_FILE}"

validate_env_variable () {
    VAR_NAME="$1"
    EXAMPLE="$2"
    PATTERN="$3"
    # Check if the variable is in the list
    # https://stackoverflow.com/questions/3685970/check-if-a-bash-array-contains-a-value
    if ! printf '%s\n\0' "${ALL_VARIABLES[@]}" | grep -Fxq -- "$VAR_NAME"
    then
        echo "$VAR_NAME is not a recognized variable."
        exit 1
    fi
    # if not set
    # ${!x} is the value of variable of name ${x}
    if [[ -z "${!VAR_NAME}" ]];
    then 
        # while not set
        while [[ -z "${!VAR_NAME}" ]] 
        do
            # read from prompt
            read -ep "${VAR_NAME} is not defined. Please enter a value: $(echo $'\n> ')" VALUE
            # assign dynamic variable 
            # see https://stackoverflow.com/questions/16553089/dynamic-variable-names-in-bash
            declare "${VAR_NAME}=${VALUE}"
            # if it doesn't match the pattern, ask again
            if [[ -n ${PATTERN} && ! "${!VAR_NAME}" =~ ${PATTERN} ]]
            then
                echo "${VAR_NAME}=\"${!VAR_NAME}\" doesn't follow the pattern \"${PATTERN}\", for example ${EXAMPLE}"
                # unset the variable to continue the while loop
                unset "${VAR_NAME}"
            else
                # set the variable in the kubeflow.env file
                save_variable "${VAR_NAME}" "${!VAR_NAME}"
                break;
            fi
        done
    fi;
    # If pattern was set, check against pattern
    if [[ -n ${PATTERN} && ! "${!VAR_NAME}" =~ ${PATTERN} ]]
    then
        echo "Warning: ${VAR_NAME}=${!VAR_NAME} doesn't follow the pattern \"${PATTERN}\""
    fi
}

save_variable () {
    VAR_NAME=$1
    VALUE=$2
    grep -Eq "^${VAR_NAME}=" ${ENV_FILE}
    if test $? -eq 0
    then
        # use sed to replace variable value in $ENV_FILE
        sed -i '' -e "s|^${VAR_NAME}=.*|${VAR_NAME}=\"${VALUE}\"|" $ENV_FILE
    else
        echo -e "${VAR_NAME}=\"${VALUE}\"" >> ${ENV_FILE}
    fi
}

get_add_ons () {
    # build list of selected add-ons
    ADD_ONS=$(grep -E '^[^#]' ./deployments/overlays/kustomization.yaml | grep 'add-ons' | awk -F"/" '{printf "%s\n", $3}')
}

validate_addons_config () {
    get_add_ons

    echo -e "The following add-ons are defined in './deployments/overlays/kustomization.yaml':"
    for add_on in ${ADD_ONS[@]}
    do
        echo "- ${add_on}"
    done
    echo -e "Checking configuration set in '${ENV_FILE}'...\n"
    for add_on in ${ADD_ONS[@]}
    do
        echo "Checking configuration of ${add_on} add-on..."
        case $add_on in
            'letsencrypt-http01')
                validate_env_variable OCI_KUBEFLOW_DOMAIN_NAME
                validate_env_variable OCI_KUBEFLOW_DOMAIN_ADMIN_EMAIL "admin@domain"
                echo "Variables for add-on ${add_on} are configured"
                ;;
            'letsencrypt-dns01') 
                validate_env_variable OCI_KUBEFLOW_DOMAIN_NAME
                validate_env_variable OCI_KUBEFLOW_DOMAIN_ADMIN_EMAIL "admin@domain"
                validate_env_variable OCI_KUBEFLOW_DNS_ZONE_COMPARTMENT_OCID "ocid1.compartment.oc1..." "ocid1\.compartment\.oc.*"
                echo "Variables for add-on ${add_on} are configured"
                ;;
            'idcs')
                validate_env_variable OCI_KUBEFLOW_IDCS_URL "https://idcs-xxxxxx.identity.oraclecloud.com" 'https://idcs-.*\.identity.oraclecloud.com$'
                validate_env_variable OCI_KUBEFLOW_IDCS_CLIENT_ID "e140ade85eec47748df546d3ba6aeca8" "[a-f0-9]{32}"
                validate_env_variable OCI_KUBEFLOW_IDCS_CLIENT_SECRET "0943f5de-eae2-4a68-c9db-d5380fe933b4" "[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
                echo "Variables for add-on ${add_on} are configured"
                ;;
            'external-mysql')
                validate_env_variable OCI_KUBEFLOW_MYSQL_USER "kubeflow" ""
                validate_env_variable OCI_KUBEFLOW_MYSQL_PASSWORD 
                validate_env_variable OCI_KUBEFLOW_MYSQL_HOST
                validate_env_variable OCI_KUBEFLOW_MYSQL_PORT "3306" "3306"
                echo "Variables for add-on ${add_on} are configured"
                ;;
            'oci-object-storage')
                validate_env_variable OCI_KUBEFLOW_OBJECT_STORAGE_BUCKET "user-kubeflow-metadata" "[a-zA-Z0-9_-]+"
                validate_env_variable OCI_KUBEFLOW_OBJECT_STORAGE_NAMESPACE "mytenancyname" "[a-z0-9]+"
                validate_env_variable OCI_KUBEFLOW_OBJECT_STORAGE_ACCESS_KEY "5cc417c90231c7dc02a9cd90e6f6ac301e46c282" "[a-f0-9]{40}"
                validate_env_variable OCI_KUBEFLOW_OBJECT_STORAGE_SECRET_KEY "sdwAAerQWE123fre3245SDFEw334=" "[a-zA-Z0-9+=]+"
                echo "Variables for add-on ${add_on} are configured"
                ;;
        esac
    done
}

setup_idcs () {
    export OCI_KUBEFLOW_ISSUER="https://${OCI_KUBEFLOW_DOMAIN_NAME:-${LBIP}}/dex"
    eval "echo \"$(cat ./oci/common/dex/overlays/idcs/config.tmpl.yaml)\"" > ./oci/common/dex/overlays/idcs/config.yaml
    eval "echo \"$(cat ./oci/common/oidc-authservice/overlays/idcs/params.tmpl.env)\"" > ./oci/common/oidc-authservice/overlays/idcs/params.env
}

setup_letsencrypt () {
    eval "echo \"$(cat ./oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-http01/kubeflow-gw.Certificate.tmpl.yaml)\"" \
    > ./oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-http01/kubeflow-gw.Certificate.yaml
    eval "echo \"$(cat ./oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-http01/letsencrypt.ClusterIssuer.tmpl.yaml)\"" \
    > ./oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-http01/letsencrypt.ClusterIssuer.yaml
    eval "echo \"$(cat ./oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-dns01/kubeflow-gw.Certificate.tmpl.yaml)\"" \
    > ./oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-dns01/kubeflow-gw.Certificate.yaml
    eval "echo \"$(cat ./oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-dns01/letsencrypt.ClusterIssuer.tmpl.yaml)\"" \
    > ./oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-dns01/letsencrypt.ClusterIssuer.yaml
    eval "echo \"$(cat ./oci/apps/kserve/domain/config-domain.tmpl.yaml)\"" \
    > ./oci/apps/kserve/domain/config-domain.yaml
}

setup_oci_object_storage () {
    eval "echo \"$(cat oci/apps/pipeline/oci-object-storage/config.tmpl)\"" > oci/apps/pipeline/oci-object-storage/config
    eval "echo \"$(cat oci/apps/pipeline/oci-object-storage/minio.tmpl.env)\"" > oci/apps/pipeline/oci-object-storage/minio.env
    eval "echo \"$(cat oci/apps/pipeline/oci-object-storage/params.tmpl.env)\"" > oci/apps/pipeline/oci-object-storage/params.env
}

setup_mysql () {
   eval "echo \"$(cat ./oci/apps/pipeline/mds-external-mysql/mysql.tmpl.env)\"" > ./oci/apps/pipeline/mds-external-mysql/mysql.env
   eval "echo \"$(cat ./oci/apps/pipeline/mds-external-mysql/mysql.Service.tmpl.yaml)\"" > ./oci/apps/pipeline/mds-external-mysql/mysql.Service.yaml
}

setup_dns_zone () {
    if ! oci dns zone get --zone-name-or-id ${OCI_KUBEFLOW_DOMAIN_NAME} > /dev/null
    then
        oci dns zone create --compartment-id ${OCI_KUBEFLOW_DNS_ZONE_COMPARTMENT_OCID} --name ${OCI_KUBEFLOW_DOMAIN_NAME} --zone-type PRIMARY \
        && echo "Please enter the nameservers above at the provider for the domain \"${OCI_KUBEFLOW_DOMAIN_NAME}\"" || echo "failed to create DNS Zone" && exit 1
    else
        echo "DNS Zone is configured for domain \"${OCI_KUBEFLOW_DOMAIN_NAME}\""
    fi
}

configure_add_ons () {
    get_add_ons
    for add_on in ${ADD_ONS[@]}
    do
        echo "Configuring ${add_on} add-on..."
        case $add_on in
            'letsencrypt-http01')
                setup_letsencrypt
                ;;
            'letsencrypt-dns01') 
                setup_dns_zone
                setup_letsencrypt
                ;;
            'idcs')
                setup_idcs
                ;;
            'external-mysql')
                setup_mysql
                ;;
            'oci-object-storage')
                setup_oci_object_storage
                ;;
        esac
    done
}

get_upstream
validate_kubectl
validate_kustomize
validate_cluster_version
echo -e "Version check successful.\n"

validate_addons_config
source ${ENV_FILE}
configure_add_ons 