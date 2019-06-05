SETUP:
1. Congigure `cluster.yaml`
2. Create a service account at https://console.cloud.google.com/apis/credentials/serviceaccountkey and save the json to `screeps-rl-credentials.json`
3. Run `export GOOGLE_APPLICATION_CREDENTIALS="screeps-rl-credentials.json"`
4. Enable the IAM API at `https://console.developers.google.com/apis/api/iam.googleapis.com/overview`
5. Go to https://console.cloud.google.com/iam-admin/iam?project=screeps-rl and change service account inheritance to "owner"

USAGE:
To launch the cluster `ray up cluster.yaml`
To submit a job: `ray submit cluster.yaml --tmux --start train.py --args=""`
To teardown the cluster `ray down cluster.yaml`