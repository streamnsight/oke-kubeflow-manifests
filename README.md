# KubeFlow distribution for Oracle Kubernetes Engine (OKE)

This release is for **KubeFlow v1.6.0**

Clone this repository and select the release branch for the KubeFlow release you wish to use.

## Requirements

KubeFlow v1.6 requires:

- kubectl v1.22+
- kustomize v3.8.8
- kubernetes cluster v1.22+

To provision a Kubernetes cluster on Oracle Cloud Infrastructure, use the OCI Console 'Quick Setup'. Ensure that the Kubernetes version is **v1.22.5 or above**.

Configure access to your Kubernetes cluster following the OCI Console information for getting access. A *Bastion Host* may be needed if you selected a Private Endpoint.

## Setup

- Clone this release.

    ```bash
    git clone --branch release/kf1.6.x https://github.com/streamnsight/oke-kubeflow-manifests.git --single-branch
    ```

- Get into the `oke-kubeflow-manifests` folder

    ```bash
    cd oke-kubeflow-manifests
    ```

- Fetch the upstream KubeFlow manifests:

    ```bash
    ./get_upstream.sh
    ```

- Create a `kubeflow.env` file using the `kubeflow.env.tmpl` template. *See each add-on option for the required details.*

    ```bash
    cp kubeflow.env.tmpl kubeflow.env
    ```

- Define the admin user and password (overriding default user@example.com):

    ```bash
    ./set_admin_pwd.sh
    ```

## Deployment Options

- Deploy the Vanilla version, with no add-on. This option deploys a minimal KubeFlow distribution, with a Load Balancer for access.

- Deploy with add-ons:
  - TLS for the Load Balancer, to insure security.
  - TLS certificates generation for your own domain name.
  - ID Cloud Service (IDCS) Integration to authenticate users.
  - OCI Managed MySQL Database Service integration in place of the MySQL deployment in the Kubernetes cluster.
  - Object Storage integration (store artifacts and pipelines in OCI Object Storage instead of the MinIO-based KubeFlow storage)

## Deploy the minimal configuration

- If you do not intend on using the other add-ons, deploy the minimal config as follows, however if you intend on using add-ons, it is recommended to configure everything once and deploy, or undeploy the vanilla deployment before deploying a version with add-ons, or risk corrupting the deployment.

    ```bash
    while ! kustomize build deployment/base | kubectl apply -f - ; do sleep 1; done;
    ```

    This deploys KubeFlow with a Flexible OCI Load Balancer.

- Open the UI:

    ```bash
    open $(kubectl get service istio-ingressgateway -n istio-system | tail -n -1 | awk '{print "http://"$4}')
    ```

## Deploy with Add-ons

### Let's Encrypt SSL Certificate generation

DNS01 Challenge is the only method that allows creation of wildcard certificates. The `letsencrypt-dns01` add-on uses OCI DNS as the DNS provider.

The letsencrypt-dns01 add-on is the default, but we provide a simpler, http01-challenge based method as well, which is simpler but more limited when it comes to serving model endpoint certificates.

The DNS01 method is preferred.

#### **Setup with HTTP01 type challenge**

- Select the `letsencrypt-http01` add-on
- Deploy the stack (!!! Make sure to configure the other add-ons before doing so)
- Set the Public IP for the load balancer as an A record on your DNS provider.

#### **Setup with DNS01 type challenge (default)**

This method uses the OCI DNS as a DNS provider.

- Select the `letsencrypt-dns01` add-on (default) in the `deployment/overlays/kustomization.yaml` file.

  (`https` and `letsencrypt-http01` add-ons should be commented out)

- Make sure you have populated the required variables in the `kubeflow.env` file for
  - `DNS_ZONE_COMPARTMENT_ID`
  - `DOMAIN_NAME`

- Create a **DNS Zone** on OCI

  Using the CLI

  ```bash
  . ./kubeflow.env
  oci dns zone create --compartment-id ${DNS_ZONE_COMPARTMENT_ID} --name ${DOMAIN_NAME} --zone-type PRIMARY
  ```

  or in the OCI Console
  - Go to **DNS Management -> DNS Zones**
  - Click **Create Zone**
  - Set **Zone Name** as the *domain name* to register
  - Select the **Compartment**
  - For **Zone Type**: keep the default of `PRIMARY`
  - Click **Create**

- Important! Take note of the URIs for the *nameservers* and set at least 2 of the 4 nameserver names as NS records at your domain name provider.

- Run the script to setup letsencrypt overlays:

  ```bash
  . ./kubeflow.env
  ./setup_letsencrypt.sh
  ```

- To use the Instance Principal auth for the DNS webhook, the cluster nodes need to have permission to alter DNS records. This requires a Dynamic Group targetting the nodes of the cluster, and a policy for this Dynamic Group:

  ```bash
  Allow dynamic-group <kubeflow_cluster_nodes> to manage dns in compartment <dns_zone_compartment_name> 
  ```

  TODO: This is pretty loose, and can be restricted

  The alternative is to provide a Secret named `oci-profile` in the `cert-manager` namespace, following these instructions:
  [https://github.com/streamnsight/cert-manager-webhook-oci#credentials](https://github.com/streamnsight/cert-manager-webhook-oci#credentials)

- Deploy the stack.

  **Important**: Make sure to configure all other add-ons before doing so.

##### **Post Deployment Setup**

- Come back to this step after deploying the stack.

- Set the Public IP from the load balancer as an `A` record on the OCI DNS Zone.

  Using the CLI

  ```bash
  . ./kubeflow.env
  DOMAIN_IP=$(kubectl get service istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
  # Set the A record pointing to the Load Balancer IP
  oci dns record rrset update --force --domain ${DOMAIN_NAME} --zone-name-or-id ${DOMAIN_NAME} --rtype 'A' --items "[{\"domain\":\"${DOMAIN_NAME}\", \"rdata\":\"${DOMAIN_IP}\", \"rtype\":\"A\",\"ttl\":300}]"
  # Set the CNAME record pointing wildcard subdomains to the root domain
  oci dns record rrset update --force --domain "*.${DOMAIN_NAME}" --zone-name-or-id ${DOMAIN_NAME} --rtype 'CNAME' --items "[{\"domain\":\"*.${DOMAIN_NAME}\", \"rdata\":\"${DOMAIN_NAME}\", \"rtype\":\"CNAME\",\"ttl\":300}]"
  ```

  Using the OCI Console
  - Go to the **DNS Zone** created earlier
  - Get the Load Balancer IP (EXTERNAL-IP)

    ```bash
    kubectl get service istio-ingressgateway -n istio-system
    ```

  - Add an `A` record with the `EXTERNAL-IP` of the Load Balancer.
  - Add a `CNAME` record with `*` as the subdomain, and the *root domain name* as the Target (for example `mykubeflow.org` if `mykubeflow.org` is the `DOMAIN_NAME`)

Note the TLS certificate can't be issued until the DNS propagates and the domain name is resolved, so it may take a while before the KubeFlow URL works properly.

Let's Encrypt will retry validating the domain name for a while. Once the Domain name is resolved by DNS, Let's Encrypt will create the certificate. This can take some time.

To check if DNS is resolving, use a tool like [https://mxtoolbox.com/SuperTool.aspx](https://mxtoolbox.com/SuperTool.aspx)

#### **IDCS Config**

- From the OCI Console, go to **Identity & Security -> Identity -> Federation**.
- Click the `OracleIdentityCloudService` provider.
- Click the **Oracle Identity Cloud Service Console URL** to get to the IDCS admin console.

  **Note**:  admin rights to the IDCS console are required to perform this step. Ask you ID admin to do this if you do not have access)

  **Note**: Any IDCS instance you manage can be used. It does not have to be the one attached to the tenancy.
- Create an App in IDCS of the type: **Confidential Application**.
- Set a name like `KubeFlow` or something identifying the usage.
- Click **Next**.
- Click **Configure this App as a client now**.
- Check the checkbox in front of `Client Credentials` and `Authorization Code` grant types.
- Provide a **Redirect URL**. KubeFlow is using Dex. The URL should be `https://<domain_name>/dex/callback`
- Click **Next**, **Next** again and then **Finish**.
- Take note of the `Client ID` and `Client Secret` and input them in the `kubeflow.env` file.
- The IDCS_URL is the full domain name of the idcs instance url of the type: `https://idcs-<xxx>.identity.oraclecloud.com` (without trailing slash)
- Click **Activate** to activate the application.

- Edit the issuer URL in IDCS **left-side menu -> Security -> OAuth -> Issuer**: Enter the same value as the `IDCS_URL` (without trailing slash)

- In IDCS **left-side menu -> Settings -> Default Settings**, make sure the **Access Signing Certificate** option is turned **ON**.

  See [https://docs.oracle.com/en/cloud/paas/identity-cloud/uaids/configure-oauth-settings.html](https://docs.oracle.com/en/cloud/paas/identity-cloud/uaids/configure-oauth-settings.html) for more details.

- Run the following commands to generate the config files:

    ```bash
    . ./kubeflow.env
    ./setup_idcs.sh
    ```

To troubleshoot issues, after deployment, check the logs of the `authservice-0` pod in namespace `auth` as well as the `dex` pod in namespace `istio-system`

#### **Users**

If you deploy IDCS, users can sign in automatically with Single Sign-On (SSO), however their user will not exist in KubeFlow and they will not be able to do anything.

For each IDCS authorized user, you will need to create a user profile like the following:

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

User namespace identifier can be anything. The kubeflow default naming convention is to use `kubeflow-<email with . and @ replaced by ->`, but that is lengthy. Prefer a simple user id

After deployment, use the `./create_user.sh` script to create a user profile and apply it automatically.

#### **MySQL external Database**

To configure a MySQL as a Service instance for KubeFlow:

- Create a MySQL DBSystem instance with the OCI Console.
  - Place the DB in a private subnet reachable by the Kubernetes Cluster nodes (either in the same subnet, or a different subnet in the same VCN).
  - **Important**: During the MySQL service creation in the OCI Console, make sure to click **Show Advanced Options**, click the **Networking** tab, and set a hostname for the database (like `mysql`). This is required to get a FQDN for the service, needed for setup.

- If you placed the MySQL service in a different subnet than the node subnet, add a Security list to configure access from the pods to the CIDR of the MySQL instance, for TCP port 3306.

- Once the DB is provisioned:
  - Get the **Full Qualified Domain Name** (FQDN) URI for the database endpoint and enter it in the `kubeflow.env` file for `DBHOST`.

- Create a `kubeflow` user.
  This is important as some of the KubeFlow components require the password to be created with the `mysql_native_password` plugin, which is not the default on the MySQL service.

  You need to run the command below within the cluster, to get access to the MySQL instance there. For this, use the `mysql.Pod.yaml` provided in this repository to spin up a MySQL client Pod:

  ```bash
  kubectl apply -f mysql.Pod.yaml
  ```

  Then get inside the pod with:

  ```bash
  kubectl exec -it mysql-temp -- /bin/bash
  ```

  Inside the Pod, run the command:

  ```bash
  mysql -u <system_user> -p -h <db_hostname> -e "create user if not exists kubeflow@'%' identified with mysql_native_password by '<kubeflow_user_password>' default role administrator;"
  ```
  providing the *system user* name (default is ADMIN when creating the DB System), the db hostname (i.e. endpoint FQDN), and the `<kubeflow_user_password>` of your choice.

  At the prompt, enter the root/system user password you provided at creation of the DB system.

  You can verify the user was created by running:

  ```bash
  mysql -u <system_user> -p -h <db_hostname> -e "select User, plugin from mysql.user;"
  ```

  You should see an entry for:
  ```bash
  | kubeflow         | mysql_native_password |
  ```

  You can then exit the pod with `exit` and delete it with
  ```bash
  kubectl delete -f mysql.Pod.yaml
  ```

- Enter the `kubeflow_user_password` you chose in the `kubeflow.env` file for `DBPASS`.
- `DBUSER` should be `kubeflow` as created above.

- Run the script `setup_mysql.sh`

  ```bash
  . ./kubeflow.env
  ./setup_mysql.sh
  ```

#### **Setup Object Storage Backend**

To use OCI Object Storage as storage for Pipelines and Pipeline Artifacts:

- Under your user icon (top right in OCI Console), go to Tenancy, and gather the `Object Storage Namespace` name of your tenancy, and the `region` code of your home region (for example `us-ashburn-1`) from the tenancy details.

  **Note**: This add-on ONLY works with the **home region** at this point, because Minio Gateway does not support other regions for S3 compatible gateways. The cluster may be in a different region, but the object storage buckets need to reside in the home region.
  
  Set the values for `REGION` and `OSNAMESPACE` in the `kubeflow.env` file.

- In the **home region**, create a bucket at the root of the tenancy (or in the compartment defined as the root for the S3 Compatibility API, which defaults to the root of the tenancy) for example `<username>-kubeflow-metadata`. Set the bucket name as `BUCKET` in the `kubeflow.env` file

- Create a **Customer Secret Key** under your user (or a user created for this purpose), which will provide you with an `Access Key` and a `Secret Access Key`. Take note of these credentials and set then as `ACCESSKEY` and `SECRETKEY` in the `kubeflow.env` file

- Run the `setup_object_storage.sh` script

  ```bash
  . ./kubeflow.env
  ./setup_object_storage.sh
  ```

### Deploy

In the `deployments/overlays/kustomization.yaml` file, comment out the add-ons you did not configure.

The defaults are:

```yaml
- ../add-ons/letsencrypt-dns01
- ../add-ons/idcs
- ../add-ons/external-mysql
- ../add-ons/oci-object-storage
```

Note that you need the `https` add-on OR `letsencrypt` add-on to enable the `idcs` add-on. Without `letsencrypt` use the Load Balancer Public IP address in place of the domain name.

To deploy, run the comand:

  ```bash
  while ! kustomize build deployments/overlays | kubectl apply -f - ; do sleep 1; done;
  ```

Be sure to get back to the post-deployment DNS setup after the manifests are deployed.

Be sure to create the user profile for your IDCS email. The KubeFlow UI should show an active namespace.

## Troubleshooting

If deployment fails due to a wrong configuration, update the `kubeflow.env`, source it, and re-run the related script(s). Then re-run the `kustomize build` and `kubectl apply` commands.

After this, you will likely need to restart the deployments with:

```bash
kubectl rollout restart deployments -n kubeflow
# for IDCS config change, also run
kubectl rollout restart deployments -n auth
kubectl rollout restart deployments -n istio-system
# For pipelines
kubectl rollout restart deployments -n knative-serving
kubectl rollout restart deployments -n knative-eventing
```

If you are having issues with meta data, pipelines and artifacts, you might need to reset the database/cache.

Use the following script that clears the MySQL database and rollout restarts deployments:

```bash
./reset_db.sh
```

## References:

DNS / Certificates
- [https://cert-manager.io/docs/configuration/acme/dns01/acme-dns/](https://cert-manager.io/docs/configuration/acme/dns01/acme-dns/)

Authentication
- [https://github.com/arrikto/oidc-authservice/blob/master/docs/media/oidc_authservice_sequence_diagram.svg](https://github.com/arrikto/oidc-authservice/blob/master/docs/media/oidc_authservice_sequence_diagram.svg)

Model Serving
- [https://knative.dev/docs/serving/using-a-custom-domain/](https://knative.dev/docs/serving/using-a-custom-domain/)
- [https://knative.dev/docs/serving/using-a-tls-cert/](https://knative.dev/docs/serving/using-a-tls-cert/)
- [https://knative.dev/docs/serving/using-auto-tls/](https://knative.dev/docs/serving/using-auto-tls/)
- [https://github.com/knative-sandbox/net-certmanager/releases](https://github.com/knative-sandbox/net-certmanager/releases)
- [https://github.com/knative-sandbox/net-certmanager/releases/download/knative-v1.7.0/net-certmanager.yaml](https://github.com/knative-sandbox/net-certmanager/releases/download/knative-v1.7.0/net-certmanager.yaml)

### Running the Examples

See the `/example` folder for examples to run KubeFlow pipelines or serve a model for inference.
