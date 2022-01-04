gcloud-auth:
	gcloud auth login
	gcloud auth application-default login

requirements-local:
	pip install -r requirements-develop.txt

unit-test:
	coverage run -m unittest tests.py
	coverage html

only-deploy:
	gcloud app deploy

deploy: unit-test only-deploy