# KubeFlow distribution for Oracle Kubernetes Engine (OKE)

## Setup

!!! First, select the latest release branch for the KubeFlow release you wish to use.

This release is for KubeFlow v1.6.0

- Fetch the upstream KubeFlow manifests:

    ```bash
    ./get_upstream.sh
    ```

- Create a `kubeflow.env` file using the `kubeflow.env.tmpl` template. See each add-on option for the required details.

- Define the admin user and password (overriding default user@example.com):

    ```bash
    ./set_admin_pwd.sh
    ```

## Deploy the minimal config

- If you do not intend on using the other add-ons, deploy the minimal config as follow:

  !! If you do want to use the add-ons, it is recommended to configure everything at once, or you will need to roll-out restart all the deployments.

    ```bash
    while ! kustomize build deployment/base | kubectl apply -f - ; do : done;
    ```

    This deploys KubeFlow with a Flexible OCI Load Balancer and a self-signed certificate for HTTPS.

- Open the UI:

    ```bash
    open $(kubectl get service istio-ingressgateway -n istio-system | tail -n -1 | awk '{print "https://"$4}')
    ```

## Deploy with Add-ons

### Let's Encrypt SSL Certificate generation

DNS01 Challenge is the only method that allows creation of wildcard certificates. The `letsencrypt-dns01` add-on uses OCI DNS as the DNS provider.

The letsencrypt-dns01 add-on is the default, but we provide a simpler, http01-challenge based method as well, which is simpler but more limited when it comes to serving model endpoint certificates.

The DNS01 method is preferred.

#### Setup with HTTP01 type challenge

- Select the `letsencrypt-http01` add-on
- Deploy the stack (!!! Make sure to configure the other add-ons before doing so)
- Set the Public IP for the load balancer as an A record on your DNS provider.

#### Setup with DNS01 type challenge (default)

This method uses the OCI DNS as a DNS provider.

- Select the `letsencrypt-dns01` add-on (default)
- Make sure you have populated the required variables in the `kubeflow.env` file
  - DNS_ZONE_COMPARTMENT_ID
  - DOMAIN_NAME

- Create a DNS Zone on OCI

  Using the CLI
  ```bash
  . ./kubeflow.env
  oci dns zone create --compartment-id ${DNS_ZONE_COMPARTMENT_ID} --name ${DOMAIN_NAME} --zone-type PRIMARY
  ```

  or in the OCI Console
  - Go to DNS Management -> DNS Zones
  - Click Create Zone
  - Zone Name is the Domain Name to register
  - Select the compartment
  - Zone Type: keep the default of `PRIMARY`
  - Click Create

- Important! Set at least 2 of the 4 nameserver names as NS records at your domain name provider.

- Run the script to setup letsencrypt overlays:
  ```bash
  ./setup_letsencrypt.sh
  ```

- Deploy the stack (!!! Make sure to configure the other add-ons before doing so)
- Set the Public IP from the load balancer as a A record on the OCI DNS Zone.

  Using the CLI
  ```bash
  DOMAIN_IP=$(kubectl get service istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
  # Set the A record pointing to the Load Balancer IP
  oci dns record rrset update --force --domain ${DOMAIN_NAME} --zone-name-or-id ${DOMAIN_NAME} --rtype 'A' --items "[{\"domain\":\"${DOMAIN_NAME}\", \"rdata\":\"${DOMAIN_IP}\", \"rtype\":\"A\",\"ttl\":300}]"
  # Set the CNAME record pointing wildcard subdomains to the root domain
  oci dns record rrset update --force --domain "*.${DOMAIN_NAME}" --zone-name-or-id ${DOMAIN_NAME} --rtype 'CNAME' --items "[{\"domain\":\"*.${DOMAIN_NAME}\", \"rdata\":\"${DOMAIN_NAME}\", \"rtype\":\"CNAME\",\"ttl\":300}]"
  ```

  Using the OCI Console
  - Go to the Zone created earlier
  - Get the Load Balancer IP (EXTERNAL-IP)
    ```bash
    kubectl get service istio-ingressgateway -n istio-system
    ```
  - Add an A record with the EXTERNAL IP of the Load Balancer
  - Add a CNAME record with '*' as a subdomain, and the root domain name as the Target.

Note the Certificate can't be issued until the DNS propagates and the domain name is resolved, so it may take a while before the KubeFlow URL works properly.

LetsEncrypt will retry validating the domain name for a while. Once the Domain name is resolved by DNS, LetsEncrypt will create the certificate. This can take some time.

### IDCS Config

- From the OCI Console, go to Identity & Security -> Identity -> Federation
- Click the OracleIdentityCloudService provider
- Click the Oracle Identity Cloud Service Console URL to get to the IDCS admin console (!!! admin rights to the IDCS console is required to perform this step. Ask you ID admin to do this if you do not have access)
- Create an App in IDCS (type: Confidential Application). Name is KubeFlow or something identifying the usage.
- Give it the `Client Credentials` and `Authorization Code` grant types.
- Provide a Redirect URL. Using Dex, it will be `https://<domain_name>/dex/callback`
- Take note of the Client ID and Client Secret and inpu them in the `kubeflow.env` file.

- Edit the issuer URL in IDCS left-side menu -> Security -> OAuth -> Issuer: Enter the instance url of the type: `https://idcs-<xxx>.identity.oraclecloud.com` (without trailing slash)

- In IDCS left-side menu -> Settings -> Default Settings, make sure the Access Signing Certificate option is turned ON.

  See [https://docs.oracle.com/en/cloud/paas/identity-cloud/uaids/configure-oauth-settings.html](https://docs.oracle.com/en/cloud/paas/identity-cloud/uaids/configure-oauth-settings.html) for more details.

- Run the following to generate the config files:

    ```bash
    ./setup_idcs.sh
    ```

To troubleshoot issues, check the logs of the `authservice-0` pod in namespace `auth` as well as the `dex` pod in namespace `istio-system`

#### Users

If you deploy IDCS, users can sign in automatically with Single Sign-On, however their user will not exist in KubeFlow and they will not be able to do anything.

For each IDCS authorized user, you need to create a user profile like the following:

```yaml
apiVersion: kubeflow.org/v1beta1
kind: Profile
metadata:
  name: <user namespace identifier>
spec:
  owner:
    kind: User
    name: <IDCS user email>
```

User namespace identifier can be anything. The kubeflow default naming convention is to use `kubeflow-`<email with . and @ replaced by -)>

Use the `./create_user.sh` script to create a user profile and apply it automatically.

### MySQL external Database

To configure a MySQL as a Service instance for KubeFlow:

- Create a MySQL DBSystem instance with the OCI Console, and place it in a private subnet reachable by the Kubernetes Cluster nodes (either in the same subnet, or a different subnet in the same VCN). Add Security lists to configure access from the pods (that use a different CIDR range) to the CIDR of the MySQL instance, for TCP port 3306.

- Create a `kubeflow` user.
  This is important as some of the KubeFlow components require the password to be created with the `mysql_native_password` plugin, which is not the default on the MySQL service.

  You need to run the command below within the cluster, to get access to the MySQL instance there. For this, use the mysql.Pod.yaml to spin up a MySQL client Pod:

  ```bash
  kubectl apply -f mysql.Pod.yaml
  ```

  Then get inside the pod with:

  ```bash
  kubectl exec -it mysql-temp -- /bin/bash
  ```

  Inside the Pod, run the command:

  ```
  mysql -u <system_user> -p -h <db_hostname> -e "create user if not exists kubeflow@'%' identified with mysql_native_password by '<kubeflow_user_password>' default role administrator;"
  ```
  At the prompt, enter the root/system user password your provided at creation of the DB system.

  You can then delete the Pod
  ```bash
  kubectl delete -f mysql.Pod.yaml
  ```

- Enter the `kubeflow_user_password` you chose in the `kubeflow.env` file.

- Run the script `setup_mysql.sh`

### Object Storage Backend

To use OCI Object Storage as storage for Pipeline and Pipeline Artifacts:

- Gather the `namespace` name of your tenancy, the `region` code (for example us-ashburn-1) from the tenancy details.
  Note: this ONLY works with the home region at this point, because Minio Gateway does not support other regions for S3 compatible gateways.

- Create a bucket at the root of the tenancy (or in the compartment defined as the root for the S3 Compatibility API, which defaults to the root of the tenancy)

- Create a Customer Secret Key under your user (or a user created for this purpose), which will provide you with an Access Key and a Secret Access Key. Take note of these credentials.

- Edit the kubeflow.env file with the details gathered.

- Run the `setup_object_storage.sh` script to generate the minio.env, config and params.env files

### Deploy

In the `deployments/overlays/kustomization.yaml` file, comment out the add-ons you did not configure.

```yaml
# - ../add-ons/https
- ../add-ons/letsencrypt-dns01
- ../add-ons/idcs
- ../add-ons/external-mysql
- ../add-ons/oci-object-storage
```

Note that you need the `https` adds OR `letsencrypt` add-on to enable the `idcs` add-on. Without `letsencrypt` use the Load Balancer Public IP address in place of the domain name. 

To deploy, run the comand:

    ```bash
    while ! kustomize build deployment/overlays | kubectl apply -f - ; do : done;
    ```

Note:

If deployment fails due to a wrong configuration, update the `kubeflow.env`, source it, and re-run the related script(s). Then re-run the kustomize build and kubectl apply commands

After this, you may still need to restart the deployments with:

```bash
kubectl rollout restart deployments -n kubeflow
# for IDCS config change, also run
kubectl rollout restart deployments -n auth
```

If you are having issues with meta data, pipelines and artifacts, you might need to reset the database/cache. 

Use the following script that clears the MySQL database and rollout restarts all deployments:

```bash
./reset_db.sh
```


References:

- [https://knative.dev/docs/serving/using-a-custom-domain/](https://knative.dev/docs/serving/using-a-custom-domain/)
- [https://knative.dev/docs/serving/using-a-tls-cert/](https://knative.dev/docs/serving/using-a-tls-cert/)
- [https://knative.dev/docs/serving/using-auto-tls/](https://knative.dev/docs/serving/using-auto-tls/)
- [https://github.com/knative-sandbox/net-certmanager/releases](https://github.com/knative-sandbox/net-certmanager/releases)
- [https://github.com/knative-sandbox/net-certmanager/releases/download/knative-v1.7.0/net-certmanager.yaml](https://github.com/knative-sandbox/net-certmanager/releases/download/knative-v1.7.0/net-certmanager.yaml)

### Inference with Kserve

```bash
COOKIE_VALUE=xxxxx...
MODEL_NAME=mnist-e2e
NAMESPACE=ns
DOMAIN_NAME=example.com
MODEL_ENDPOINT=${MODEL_NAME}.${NAMESPACE}.${DOMAIN_NAME}

curl -v -L -X POST -d @./input.json {} -H "Cookie: authservice_session=${COOKIE_VALUE}" -H "Host: ${MODEL_ENDPOINT}" https://${MODEL_ENDPOINT}/v1/models/${MODEL_NAME}:predict
```

```json

```