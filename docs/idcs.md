# IDCS Config

## Create an IDCS Application

- From the OCI Console, go to **Identity & Security -> Identity -> Federation**.
- Click the **OracleIdentityCloudService** provider.
- Click the **Oracle Identity Cloud Service Console URL** to get to the IDCS admin console.

    ***Note**: admin rights to the IDCS console are required to perform this step.
    Ask you ID admin to do this if you do not have access.*

    ***Note**: Any IDCS instance you manage can be used. It does not have to be the one attached to the tenancy.*
- Create an App in IDCS (type: **Confidential Application**).
- Set a name like **KubeFlow** or something identifying the usage.
- Check **Display in My Apps** so the user can see the KubeFlow app in their list of apps. Since when logging out, the user is redirected back to the IDCS console, this is where the user can see the app to log back into KubeFlow.
- If you want to allow users to request access, 
- Click **Next**.
- Click **Configure this App as a client now**.
- Check the checkbox in front of **Client Credentials** and **Authorization Code** grant types.
- Provide a Redirect URL. Using Dex, it will be `https://<domain_name>/dex/callback`. 

    When not using a domain name, enter the public load balancer IP adress.

- If you want to control who can use the app (rather then just authenticate with IDCS), select the **Enforce Grants as Authorization** checkbox under **Authentication and Authorization**. You will then need to add Users to this app to allow them to use it, or if you checked **Users can request access** they will be able to self-register.

- Click **Next**, **Next** and **Finish**.
- Take note of the **Client ID** and **Client Secret** and input them in the `kubeflow.env` file.
- The `OCI_KUBEFLOW_IDCS_URL` variable is the full domain name of the idcs instance url of the type: `https://idcs-<xxx>.identity.oraclecloud.com` (without trailing slash)
- Click **Activate** to activate the application.

- Edit the issuer URL in **IDCS left-side menu -> Security -> OAuth -> Issuer**: Enter the same value as the `OCI_KUBEFLOW_IDCS_URL` (without trailing slash)

- In **IDCS left-side menu -> Settings -> Default Settings**, make sure the **Access Signing Certificate** option is turned **ON**.

  See [https://docs.oracle.com/en/cloud/paas/identity-cloud/uaids/configure-oauth-settings.html](https://docs.oracle.com/en/cloud/paas/identity-cloud/uaids/configure-oauth-settings.html) for more details.

## Troubleshooting

To troubleshoot issues, after deployment, check the logs of the `authservice-0` pod in namespace `auth` as well as the `dex` pod in namespace `istio-system`

## Legacy scripts

Shell scripts are also available in the `scripts` folder.

