# Sklearn Model Serving with KServe on KubeFlow

Adapted from [https://kserve.github.io/website/modelserving/v1beta1/sklearn/v2/](https://kserve.github.io/website/modelserving/v1beta1/sklearn/v2/)

## Training

```python
from sklearn import svm
from sklearn import datasets
from joblib import dump

iris = datasets.load_iris()
X, y = iris.data, iris.target

clf = svm.SVC(gamma='scale')
clf.fit(X, y)

dump(clf, 'model.joblib')
```

The model.joblib file is the trained model. It needs to be posted on some reachable storage.

Posted on a bucket with a Pre-Auth request here: [https://objectstorage.us-sanjose-1.oraclecloud.com/p/xKuRUl7hf7BE3t0G4aPakNb4n73cCrZ1zTNQadtW2XBzJFzhT6j8aIsWbvViir7C/n/bigdatadatasciencelarge/b/epleroy-public-models/o/model.joblib](https://objectstorage.us-sanjose-1.oraclecloud.com/p/xKuRUl7hf7BE3t0G4aPakNb4n73cCrZ1zTNQadtW2XBzJFzhT6j8aIsWbvViir7C/n/bigdatadatasciencelarge/b/epleroy-public-models/o/model.joblib)

This URL is passed in the InferenceModel yaml:

```yaml
apiVersion: "serving.kserve.io/v1beta1"
kind: "InferenceService"
metadata:
  name: "sklearn-irisv2"
spec:
  predictor:
    sklearn:
      protocolVersion: "v2"
      storageUri: "https://objectstorage.us-sanjose-1.oraclecloud.com/p/xKuRUl7hf7BE3t0G4aPakNb4n73cCrZ1zTNQadtW2XBzJFzhT6j8aIsWbvViir7C/n/bigdatadatasciencelarge/b/epleroy-public-models/o/model.joblib"
```

## Call the Inference Server:

Create the payload as `inputs.json`

```json
{
  "inputs": [
    {
      "name": "input-0",
      "shape": [2, 4],
      "datatype": "FP32",
      "data": [
        [6.8, 2.8, 4.8, 1.4],
        [6.0, 3.4, 4.5, 1.6]
      ]
    }
  ]
}
```

### Get the cookie from the KubeFlow UI

Option+Command+i on Mac OS get you into the Developer Tools

Under Application, look for Cookies, and especially look for the `authservice_session` cookie.
Copy the value of the cookie.

then run:

```bash
export COOKIE_VALUE=xxxxxxxxxxxdNa1pZUWtsUFFsSkhWRmMzVGpkRFExTmFTRWRUUms5Q04wMU1WalJQUkU4M05qSlBVa2RUU3pRMVRsRkxVMEU9fO-F8FEGEuzz3rLPXalgkzzzzzzzzz
export MODEL_NAME=sklearn-irisv2
export NAMESPACE=<yournamespace>
export DOMAIN_NAME=<your_domain_name>
export MODEL_ENDPOINT="${MODEL_NAME}.${NAMESPACE}.${DOMAIN_NAME}"

curl -v -L -X POST -d @./inputs.json -H "Content-Type: application/json" -H "Cookie: authservice_session=${COOKIE_VALUE}" -H "Host: ${MODEL_ENDPOINT}" https://$MODEL_ENDPOINT/v2/models/$MODEL_NAME/infer
```
