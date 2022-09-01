# KubeFlow distribution for Oracle Kubernetes Engine (OKE)

## Setup

- Fetch the upstream KubeFlow manifests:

    ```bash
    ./get_upstream.sh
    ```

- Define the admin user and password (overriding default user@example.com):

    ```bash
    ./set_admin_pwd.sh
    ```

- Deploy the minimal config:

    ```bash
    while ! kustomize build deployment/base | kubectl apply -f - ; do : done;
    ```

    This deploys KubeFlow with a Flexible OCI Load Balancer and a self-signed certificate for HTTPS.

- Open the UI:

    ```bash
    open $(kubectl get service istio-ingressgateway -n istio-system | tail -n -1 | awk '{print "https://"$4}')
    ```

## Add-ons

### Let's Encrypt SSL Certificate generation

To setup Let's Encrypt with your own domain, first setup the base distribution, get the load balancer public IP, and add an A record on your domain DNS. 

Verify that the domain propagates to your KubeFlow deployment before attempting to setup Lets Encrypt certificate generation.

To deploy the overlay, run the script:

```bash
./setup_letsencrypt.sh
```

You'll be prompted for your domain name, and the domain admin email (required for Lets Encrypt)

The overlay creates a `ClusterIssuer` for Lets Encrypt with `cert-manager`, a `Certificate` for the domain, and modifies the `authservice` configuration to white-list the `/.well-known/` path providing access to the Let's Encrypt token verification.

### IDCS Config

This config still uses Dex.

TODO: bypass Dex altogether?

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

To troubelshoot issues, check the logs of the `authservice-0` pod in namespace `auth` as well as the dex pod in namespace `istio-system`

### MySQL external Database

To configure a MySQL as a Service instance for KubeFlow:

- Create a MySQL DBSystem instance with the OCI Console, and place it in a private subnet reachable by the Kubernetes Cluster nodes (either in the same subnet, or a different subnet in the same VCN). Add Security lists to configure access from the pods (that use a different CIDR range) to the CIDR of the MySQL instance, for TCP port 3306.

- Create a `kubeflow` user.
  This is important as some of the KubeFlow components require the password to be created with the `mysql_native_password` plugin, which is not the default on the MySQL service.

  From a MySQL client, run:
  ```
  mysql -u <system_user> -p <system_password> -h <db_hostname> -e "create user if not exists kubeflow@'%' identified with mysql_native_password by '<kubeflow_user_password>' default role administrator;"
  ```
- Enter the `kubeflow_user_password` you chose in the `kubeflow.env` file.

- Run the script `setup_mysql.sh`