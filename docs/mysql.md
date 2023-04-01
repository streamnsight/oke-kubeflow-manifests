# Set Up a Managed MySQL Database for KubeFlow

## Provision the Database

To configure a MySQL as a Service instance for KubeFlow in the OCI Console:

- Create a **MySQL DBSystem** instance with the OCI Console.
  - Place the DB in a private subnet reachable by the Kubernetes Cluster nodes (either in the same subnet, or a different subnet in the same VCN).

  - **IMPORTANT NOTE**: **A DNS hostname must be provided.** This is required to get a FQDN for the service, needed for setup.
  
    - Click **Show Advanced Options**.
    - Click the **Networking** tab, 
    - Set a **hostname** for the database (like `mysql`).

- If you placed the MySQL service in a different subnet than the node subnet, add a Security list to configure access from the pods (that uses a different CIDR range) to the CIDR of the MySQL instance, for TCP port 3306.

## Create the `kubeflow` user

- Once the DB is provisioned:
  - Get the FQDN URI for the database and enter it in the `kubeflow.env` file for `OCI_KUBEFLOW_MYSQL_HOST`.

- Create a `kubeflow` user.
  This is important as some of the KubeFlow components require the password to be created with the `mysql_native_password` plugin, which is not the default on the MySQL service.

  To create the user, the MySQL system admin should run the following SQL in a mysql client (replacing the `<kubeflow_user_password>` with a password of your choice):

    ```sql
    create user if not exists kubeflow@'%' identified with mysql_native_password by '<kubeflow_user_password>' default role administrator;
    ```

  This can be done by running the command in a mysql pod within the cluster, to get access to the MySQL instance from there. For this, use the mysql.Pod.yaml to spin up a MySQL client Pod:

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
  providing the system user name (default is ADMIN when creating the DB System), the db hostname, and the kubeflow_user_password of your choice.

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

- Enter the `kubeflow_user_password` you chose in the `kubeflow.env` file for `OCI_KUBEFLOW_MYSQL_PASSWORD`.
- `OCI_KUBEFLOW_MYSQL_USER` should be `kubeflow` as created above.
