# Create User Profiles

After deployment, for each IDCS authorized user, you will need to create a user profile.

User profiles can be created with:

```bash
./okf user create
```

Follow the prompts to create the profile

Alternatively a user can be created without prompts with:

```bash
./okf user create -E <email> -U <username> --kpf
```

the `--kfp` flag applies a PodDefault to the namespace providing the credentials for a notebook to run KFP pipelines.

## Under the hood

The user profile has the following manifest:

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

## Legacy script

After deployment, use the `./create_user.sh` script to create a user profile and apply it automatically.
