 Testing Services
 ===

Config File
---
We expect an YAML file together the main.py file, with this structure:

```yaml
TOKEN: <TOKEN TO ACCESS THE HTTP ENDPOINT AND TCP> String 
TIMEOUT: <GLOBAL TIMEOUT> Int 
TCP_SERVICE_ADDRESS: <TCP SERVICE ADDRESS, CAN BE A NAME OR IP> String
TCP_SERVICE_PORT: <TCP PORT TO CONNECT, IF NOT SUPPLIED AN ERROR WILL BE RAISED> Int
HTTP_SERVICE_ADDRESS: <HTTP/HTTPS SERVICE ADDRESS, CAN BE A NAME OR IP> String
CHECK_INTERVAL: <INTERVAL BEETWEEN CHECKS> Int
HEALTHY_THRESHOLD: <COUNTS HOW MANY SUCCESS AN SERVICE WILL BE DECLARED OK> Int
UNHEALTHY_THRESHOLD: <COUNTS HOW MANY SUCCESS AN SERVICE WILL BE DECLARED FAILED> Int
LOG_LEVEL: <LOG LEVEL, ACCEPTED VALUES fatal, critical, info, error, debug>
SMTP: #SMTP DEFINITIONS
  USERNAME: <USERNAME USED TO AUTH ON SMTP SERVICE. ONLY AUTH SMTP SERVICE WILL WORK>
  PASSWORD: <PASSOWRD FOR SMTP SERVICE
  HOST: <SMTP HOST>
  PORT: <SMTP PORT, COMMON PORTS 465, 587>
  FROM: <FROM FIELD ON E-MAIL>
  TO:
    - <USERS WILL BE RECEIVE THE EMAIL NOTIFICATION>
    - <CAN BE MULTIPLES ADDRESSES>
```
All options are required.

Developing
---

Install the local requirements with this command:
```shell
pip install -r requirements-development.txt
```

Running Unit test
---
```shell
make unit-test
```

Deploying Pre-reqs
---
Gcloud-sdk must be installed. For more information, see [here](https://cloud.google.com/sdk/docs/install).
Ensure gcloud is authenticated, project defined and have activated service account for your user (or SA)
```shell
gcloud auth login
gcloud config set project <PROJECT_NAME>
gcloud auth application-default login
```

or simply run:
```shell
make gcloud-auth
```

Install app engine components for python
```shell
gcloud components install app-engine-python
```

The steps above can be executed once.

Deploy
---
To deploy, run:
```shell
gcloud app deploy
```

or run:
```shell
make deploy
```

TODO / FIX
---
- Handle better with secrets, a better approach is use google kms
- save the services states on memcached, not in memory
- improve logic to avoid error repeated error messages
- implement a rss endpoint. I've implemented a simple http endpoint.