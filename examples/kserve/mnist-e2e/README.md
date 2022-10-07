# MNIST End-to-End pipeline

- Creates a Katib Experiment to do Hyperparameters tuning
- Saves the best results in a volume
- Train the MNIST model with TensorFlow in a TFjob
- Deploy the model with KServe

## Setup

- Deploy the PodDefault template in the user namespace to be able to call KubeFlow Pipelines (KFP) from the Notebook

```bash
kubectl apply -f access-kf-pipeline.PodDefault.yaml
```

- Create a Jupyter Notebook and make sure to select the `Allow Access to KFP` in the Configurations section.

- Import the `MNIST-e2e.ipynb` Notebook in your Jupyter session.

- Run the Notebook

## Inference using Curl

Using curl, inference can be performed with the following:

The mnist-e2e-9.json payload is the number 9 image formated as binary in a json object. See the notebook for how to generte this payload.

```bash
export COOKIE_VALUE="<authservice-session cookie value from browser>"
export MODEL_NAME=mnist-e2e
export NAMESPACE="<your_namespace>"
export DOMAIN_NAME="<your_domain>"
export MODEL_ENDPOINT="${MODEL_NAME}.${NAMESPACE}.${DOMAIN_NAME}"

curl -v -L -X POST -d @./mnist-e2e-9.json -H "Cookie: authservice_session=${COOKIE_VALUE}" -H "Host: ${MODEL_ENDPOINT}" -H "Content-Type: application/json" https://$MODEL_ENDPOINT/v1/models/$MODEL_NAME:predict
```

Output should look like:

```bash
{
    "predictions": [
        {
            "classes": 9,
            "predictions": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
        }
    ]
}
```

References:

- [https://github.com/kubeflow/pipelines/blob/2.0.0b4/samples/contrib/kubeflow-e2e-mnist/kubeflow-e2e-mnist.ipynb](https://github.com/kubeflow/pipelines/blob/2.0.0b4/samples/contrib/kubeflow-e2e-mnist/kubeflow-e2e-mnist.ipynb)
- [https://github.com/KServe/KServe/tree/master/docs/samples/istio-dex](https://github.com/KServe/KServe/tree/master/docs/samples/istio-dex)

