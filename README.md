# KubeFlow distribution for Oracle Kubernetes Engine (OKE)

## Setup

!!! First, select the latest release branch for the KubeFlow release you wish to use.

This release is for KubeFlow v1.6.0

- Fetch the upstream KubeFlow manifests:

    ```bash
    ./get_upstream.sh
    ```

- Create a `kubeflow.env` file using the `kubeflow.env.tmpl` template. See each add-on option for the required details

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

To setup Let's Encrypt with your own domain, first setup the base distribution, get the load balancer public IP, and add an A record on your domain DNS. 

Verify that the domain propagates to your KubeFlow deployment before attempting to setup Lets Encrypt certificate generation.

To deploy the overlay, run the script:

```bash
./setup_letsencrypt.sh
```

You'll be prompted for your domain name, and the domain admin email (required for Lets Encrypt)

The overlay creates a `ClusterIssuer` for Lets Encrypt with `cert-manager`, a `Certificate` for the domain, and modifies the `authservice` configuration to white-list the `/.well-known/` path providing access to the Let's Encrypt token verification.

Note: when you use LetsEncrypt, you run into a situation where the domain name needs to have the Load Balancer IP address, before the Load Balancer is actually created. You need to run the deployment, then get the IP address of the load balancer with:

```bash
kubectl get service istio-ingressgateway -n istio-system
```

Add this IP as a A record on your Domain Name with the IP address.

LetsEncrypt will retry validating the domain name for a while. Once the Domain name is resolved by DNS, LetsEncrypt will create the certificate. This can take some time.

### IDCS Config

- Create an App in IDCS (Confidential Application)
- Give it the `Client Credentials` and `Authorization Code` grant types.
- Provide a Redirect URL. Using Dex, it will be `https://<domain_name>/dex/callback`
- Take note of the Client ID and Client Secret

- Follow these instructions below to edit the issuer URL in IDCS left-side menu -> Security -> OAuth -> Issuer: Enter the instance url of the type: `https://idcs-<xxx>.identity.oraclecloud.com/`

- In IDCS left-side menu -> Settings -> Default Settings, make sure the Access Signing Certificate option is turned ON.

https://docs.oracle.com/en/cloud/paas/identity-cloud/uaids/configure-oauth-settings.html

- Run the following to generate the config files:

    ```bash
    ./setup_idcs.sh
    ```

To troubleshoot issues, check the logs of the `authservice-0` pod in namespace `auth` as well as the dex pod in namespace `istio-system`


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

- Create a bucket at the root of the tenancy (or in the compartment defined as the root for the S3 Compatibility API, which defaults to the root of the tenancy)

- Create a Customer Secret Key under your user (or a user created for this purpose), which will provide you with an Access Key and a Secret Access Key. Take note of these credentials.

- Run the `setup_object_storage.sh` script to generate the minio.env and params.env files

### Deploy

In the `deployments/overlays/kustomization.yaml` file, comment out the add-ons you did not configure.

```yaml
# - ../add-ons/https
- ../add-ons/letsencrypt
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

After this, you may still need to restart the deployments with 

```bash
kubectl rollout restart deployments -n kubeflow
# for IDCS config change, also run
kubectl rollout restart deployments -n auth
```