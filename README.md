# KubeFlow distribution for Oracle Kubernetes Engine (OKE)

**This release is for KubeFlow v1.6**

## Requirements

To deploy, you need:

- OCI Command Line Interface v3.5+
- kubectl 1.22+
- kustomize v3.7+ (support for Components)
- A Kubernetes cluster v1.22+

## Setup

!!! First, clone the repository and select the latest release branch for the KubeFlow release you wish to use.

```bash
git clone --branch release/kf1.6 https://github.com/streamnsight/oke-kubeflow-manifests.git
```

- Run the CLI config:

  ```bash
  ./okf config
  ```

## Deploy the minimal config

- If you do not intend on using the other add-ons, deploy the minimal config as follow:

  !! If you do want to use the add-ons, it is recommended to configure everything at once, or you will need to roll-out restart all the deployments.

  Edit the `./deployments/overlays/kustomization.yaml` file and comment out the add-ons.

- Run:

  ```bash
  ./okf deploy
  ```

- Open the UI:

    ```bash
    open $(kubectl get service istio-ingressgateway -n istio-system | tail -n -1 | awk '{print "https://"$4}')
    ```

## Deploy with Add-ons

Edit the `./deployments/overlays/kustomization.yaml` file and comment out the add-ons you do not wish to use.

### Let's Encrypt SSL Certificate generation

DNS01 Challenge is the only method that allows creation of wildcard certificates. The `letsencrypt-dns01` add-on uses OCI DNS as the DNS provider.

The letsencrypt-dns01 add-on is the default, but we provide a simpler, http01-challenge based method as well, which is simpler but more limited when it comes to serving model endpoint certificates.

The DNS01 method is preferred.

#### Setup with HTTP01 type challenge

- Select the `letsencrypt-http01` add-on in the `./deployments/overlays/kustomization.yaml` file
 (https and letsencrypt-dns01 add-ons should be commented out)
- Run

    ```bash
    ./okf config
    ```

- Deploy the stack (!!! Make sure to configure the other add-ons before doing so)
- Set the Public IP for the load balancer as an A record on your DNS provider.

#### Setup with DNS01 type challenge (default)

This method uses the OCI DNS as a DNS provider.

- Select the `letsencrypt-dns01` add-on (default) in the `deployment/overlays/kustomization.yaml` file
 (https and letsencrypt-http01 add-ons should be commented out)

- Make sure you have populated the required variables in the `kubeflow.env` file for
  - OCI_KUBEFLOW_DNS_ZONE_COMPARTMENT_ID
  - OCI_KUBEFLOW_DOMAIN_NAME

- Run the config command to configure everything automatically

  ```bash
  ./okf config
  ```

The setup may fail if you do not have credentials to manage DNS Zones.

Manual setup consists in:

- Create a DNS Zone on OCI

  Using the CLI

  ```bash
  . ./kubeflow.env
  oci dns zone create --compartment-id ${OCI_KUBEFLOW_DNS_ZONE_COMPARTMENT_OCID} --name ${OCI_KUBEFLOW_DOMAIN_NAME} --zone-type PRIMARY
  ```

  or in the OCI Console
  - Go to DNS Management -> DNS Zones
  - Click Create Zone
  - Set Zone Name as the Domain Name to register
  - Select the compartment
  - Zone Type: keep the default of `PRIMARY`
  - Click Create

- Important! Note the URIs for the nameservers and set at least 2 of the 4 nameserver names as NS records at your domain name provider.

- To use the Instance Principal auth for the DNS webhook, the cluster nodes need to have permission to alter DNS records. This requires a Dynamic Group targetting the nodes of the cluster, and a policy for this Dynamic Group:

  ```bash
  Allow dynamic-group <kubeflow_cluster_nodes> to manage dns in compartment <dns_zone_compartment_name> 
  ```

  TODO: This is pretty loose, and can be restricted

  The alternative is to provide a Secret named `oci-profile` in the `cert-manager` namespace, following these instructions:
  [https://github.com/streamnsight/cert-manager-webhook-oci#credentials](https://github.com/streamnsight/cert-manager-webhook-oci#credentials)

##### Post Deployment Setup

The `./okf deploy` command will update the DNS records, but may fail if you do ot have the required permissions to manage DNS Zone.

If it fails, after deploying the stack, manual setup consists of:

- Set the Public IP from the load balancer as a A record on the OCI DNS Zone.

  Using the CLI

  ```bash
  . ./kubeflow.env
  DOMAIN_IP=$(kubectl get service istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
  # Set the A record pointing to the Load Balancer IP
  oci dns record rrset update --force --domain ${OCI_KUBEFLOW_DOMAIN_NAME} --zone-name-or-id ${OCI_KUBEFLOW_DOMAIN_NAME} --rtype 'A' --items "[{\"domain\":\"${OCI_KUBEFLOW_DOMAIN_NAME}\", \"rdata\":\"${DOMAIN_IP}\", \"rtype\":\"A\",\"ttl\":300}]"
  # Set the CNAME record pointing wildcard subdomains to the root domain
  oci dns record rrset update --force --domain "*.${OCI_KUBEFLOW_DOMAIN_NAME}" --zone-name-or-id ${OCI_KUBEFLOW_DOMAIN_NAME} --rtype 'CNAME' --items "[{\"domain\":\"*.${OCI_KUBEFLOW_DOMAIN_NAME}\", \"rdata\":\"${OCI_KUBEFLOW_DOMAIN_NAME}\", \"rtype\":\"CNAME\",\"ttl\":300}]"
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

To check if DNS is resolving, use a tool like [https://mxtoolbox.com/SuperTool.aspx](https://mxtoolbox.com/SuperTool.aspx)

### IDCS Config

- Create an IDCS application and pupulate the `OCI_KUBEFLOW_IDCS_CLIENT_ID`, `OCI_KUBEFLOW_IDCS_CLIENT_SECRET`, and `OCI_KUBEFLOW_IDCS_URL` values in the `kubeflow.env` environment variables file.

See details on [creating the IDCS application](./docs/idcs.md).

#### IDCS Users

If you deploy IDCS, users can sign in automatically with Single Sign-On, however their user will not exist in KubeFlow and they will not be able to do anything.

Once KubeFlow is deployed, follow instructions to [create users](./docs/user-profiles.md).

### MySQL external Database

- Deploy a Managed MySQL Database instance on OCI, making sure a `hostname` is defined during creation.

  See details and important notes for creation in [Set Up a Managed MySQL Database for KubeFlow](./docs/mysql.md)

- Create the KubeFlow user.

  If you are not the system admin, follow instructions in [Set Up a Managed MySQL Database for KubeFlow](./docs/mysql.md) and have your sysadmin create the KubeFlow user.

  If you have the sys/admin username and password, use:

  ```bash
  ./okf mysql create-kf-user
  ```

  and follow prompts to create the KubeFlow user, or run in one line with:

  ```bash
  ./okf mysql create-kf-user -u kubeflow -p <kubeflow_user_password> -U ADMIN -P <sysadmin_password> -y
  ```

- Enter the environment variables in the `kubeflow.env` file.

  - `OCI_KUBEFLOW_MYSQL_PASSWORD` should be the `<kubeflow_user_password>` you chose when creating the KubeFlow user.
  - `OCI_KUBEFLOW_MYSQL_USER` should be `kubeflow` as created above.
  - `OCI_KUBEFLOW_MYSQL_HOST` should be the FQDN URI for the database found in the database system details.

### Setup Object Storage Backend

To use OCI Object Storage as storage for Pipelines and Pipeline Artifacts:

- Under your user icon (top right in OCI Console), go to Tenancy, and gather the `Object Storage Namespace` name of your tenancy, and the `region` code of your home region (for example `us-ashburn-1`) from the tenancy details.
  Note: Object Storage integration currently ONLY works with the **home region**, because Minio Gateway does not support other regions for S3 compatible gateways.
  
  Set the values for `OCI_KUBEFLOW_OBJECT_STORAGE_REGION` and `OCI_KUBEFLOW_OBJECT_STORAGE_NAMESPACE` in the `kubeflow.env` file.

- Create a bucket at the root of the tenancy (or in the compartment defined as the root for the S3 Compatibility API, which defaults to the root of the tenancy) for example `<username>-kubeflow-metadata`. Set the bucket name as `OCI_KUBEFLOW_OBJECT_STORAGE_BUCKET` in the `kubeflow.env` file

- Create a **Customer Secret Key** under your user (or a user created for this purpose), which will provide you with an `Access Key` and a `Secret Access Key`. Take note of these credentials and set then as `OCI_KUBEFLOW_OBJECT_STORAGE_ACCESS_KEY` and `OCI_KUBEFLOW_OBJECT_STORAGE_SECRET_KEY` respectively in the `kubeflow.env` file

### Configure Add-ons Manifests

- In the `deployments/overlays/kustomization.yaml` file, comment out the add-ons you do not wish to use.

  The defaults are:

  ```yaml
  - ../add-ons/letsencrypt-dns01
  - ../add-ons/idcs
  - ../add-ons/external-mysql
  - ../add-ons/oci-object-storage
  ```

  Note that you need the `https` adds OR `letsencrypt` add-on to enable the `idcs` add-on. Without `letsencrypt` use the Load Balancer Public IP address in place of the domain name.

- Configure add-ons with:

  ```bash
  ./okf config
  ```

  It will use the default `kubeflow.env` file to configure add-ons. TO use an alternative environment variables file, us the `-e <env_file>` flag.

### Build and Deploy KubeFlow Manifests

The easiest way to deploy, is using the CLI with:

  ```bash
  ./okf deploy
  ```

It will take care of post-deploy tasks, like setting up DNS entries with the load balancer public IP.

To deploy manually, after running `./oke config`, you can also run the command:

  ```bash
  while ! kustomize build deployments/overlays | kubectl apply -f - ; do sleep 1; done;
  ```

Be sure to get back to the post-deployment DNS setup after the manifests are deployed.

When using the while loop, the istio side-car containers sometimes fail to mount. In the case where you see TLS errors in the UI, it is likely you need to run a rollout restart of the pods in the kubeflow namespace.

  ```bash
  kubectl rollout restart deployments -n kubeflow
  # for IDCS config change, also run
  kubectl rollout restart deployments -n auth
  kubectl rollout restart deployments -n knative-serving
  ```

### Create Users

Be sure to create the user profile for your IDCS email. The KubeFlow UI should show an active namespace.

Note:

If deployment fails due to a wrong configuration, update the `kubeflow.env`, and re-run the deploy command.


## Troubleshooting

If you are having issues with meta data, pipelines and artifacts, you might need to reset the database/cache.

Use the following script that clears the MySQL database and rollout restarts all deployments:

```bash
./okf mysql reset-db
```

**Important:** This command will clear all caches and pipelines for all users, and is a pretty drastic measure recommended if issues happen during setup. Run this with caution.


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

See the /example folder for examples to run KubeFlow pipelines or serve a model for inference.
