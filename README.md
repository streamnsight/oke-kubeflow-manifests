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

