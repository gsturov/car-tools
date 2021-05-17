#!/usr/bin/python3

NAMESPACE = 'cp4s'

import sys, base64, requests, subprocess, urllib3, json
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def ignore_404(f):
    try:
        return f()
    except ApiException as e:
        if e.status != 404:
            raise e

def decode(s):
    return base64.b64decode(s).decode()

def b64(s):
    if type(s) == str: s = s.encode()
    return base64.b64encode(s).decode()

class SecretData(object):
    def __init__(self, name):
        self.name = name

    def load(self):
        core_v1 = client.CoreV1Api(client.api_client.ApiClient())
        self.data = ignore_404(lambda: core_v1.read_namespaced_secret(self.name, NAMESPACE).data)
        return self.data

    def item(self, item_name):
        return self.data and decode(self.data[item_name]) or None


config.load_kube_config()
car_system_id_secret = SecretData('car-connector-config-system-id')
if not car_system_id_secret.load(): raise Exception('car-connector-config-system-id Secret is not accessible.')
rsa_private = car_system_id_secret.item('systemid.private.pem')
rsa_public = car_system_id_secret.item('systemid.public.pem')

privkey = serialization.load_pem_private_key(rsa_private.encode(), password=None, backend=default_backend())
sig = privkey.sign('car-connector-config'.encode(), padding.PKCS1v15(), hashes.SHA256())
application_token = f'{b64("car-connector-config")}.{b64(sig)}'

res = subprocess.run(['oc', 'get', 'route', '-n', NAMESPACE, 'isc-route-default', '-o', "jsonpath='{.spec.host}'"], stdout=subprocess.PIPE)
hostname = res.stdout.decode('utf-8').replace("'", '')
print('Service hostname: ', hostname)


resp = requests.get(f'https://{hostname}/api/entitlements/v1.0/authToken/listAccounts', headers={'authorization': application_token})
if (resp.status_code != 200):
    print('Error when accessing "listAccounts" endpoint: ', resp.status_code); sys.exit(1)

for account in resp.json():
    body = {'systemIdName': 'car-connector-config.UDSConnection', 'storedMessage': {}}
    resp = requests.post(f'https://{hostname}/api/entitlements/v1.0/authToken', headers={'authorization': application_token}, json=True, data=json.dumps(body))
    if (resp.status_code != 200):
        print('Error when accessing "authToken" endpoint: ', resp.status_code); sys.exit(1)
    auth_token = resp.json()['token']
    print(auth_token)

    body = { 'token': auth_token, 'onBehalfOf': account }
    resp = requests.post(f'https://{hostname}/api/entitlements/v1.0/authToken/exchangeAuthToken', headers={'authorization': application_token}, json=True, data=json.dumps(body))
    if (resp.status_code != 200):
        print('Error when accessing "exchangeAuthToken" endpoint: ', resp.status_code); sys.exit(1)
    jwt = resp.json()['jwt']
    print(jwt)

    key_id = f'auto-generated-CAR-service-access-key-{account}'
    headers = {'Authorization': f'Bearer {jwt}', 'Content-Type': 'application/json'}
    resp = requests.post(f'https://{hostname}/api/apikey/create', data=json.dumps({'id': key_id}), headers=headers)
    if (resp.status_code != 200):
        print('Error when accessing "apikey/create" endpoint: ', resp.status_code); sys.exit(1)
    key = resp.json()
    print(key)

    break
