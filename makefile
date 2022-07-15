.PHONY: build
.PHONY: push
.PHONY: schedule
.PHONY: job
.PHONY: deploy

build:
	docker build -t eu.gcr.io/github-backup-355409/gitbackup:latest .

push:
	docker push eu.gcr.io/github-backup-355409/gitbackup:latest

schedule:
	#
	#maybe this? Need to look into this more

	#gcloud scheduler jobs create http (
	#	("Github backup job": --location="europe-west6")
	#	--schedule="0 23 * * 0-6"
	#	--uri="https://europe-west9-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/github-backup-355409/jobs/github-backup:run"
	#	--http-method=POST
	#)

job:
	#
	# "figure out how to create job"
	#

deploy:	build push job schedule