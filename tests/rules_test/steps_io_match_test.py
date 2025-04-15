from tests.helper import parse_workflow_string
from validate_actions import LintProblem, rules


def test_io_no_match():
    workflow_string = """
name: 'Deploy to Cloud Run from Source'

on:
  push:
    branches:
      - '$default-branch'

env:
  PROJECT_ID: 'my-project' # TODO: update to your Google Cloud project ID
  REGION: 'us-central1' # TODO: update to your region
  SERVICE: 'my-service' # TODO: update to your service name

jobs:
  deploy:
    runs-on: 'ubuntu-latest'

    permissions:
      contents: 'read'
      id-token: 'write'

    steps:
      - name: 'Checkout'
        uses: 'actions/checkout@692973e3d937129bcbf40652eb9f2f61becf3332' # actions/checkout@v4

      # Configure Workload Identity Federation and generate an access token.
      #
      # See https://github.com/google-github-actions/auth for more options,
      # including authenticating via a JSON credentials file.
      - id: 'auth'
        name: 'Authenticate to Google Cloud'
        uses: 'google-github-actions/auth@f112390a2df9932162083945e46d439060d66ec2' # google-github-actions/auth@v2
        with:
          workload_identity_provider: 'projects/123456789/locations/global/workloadIdentityPools/my-pool/providers/my-provider' # TODO: replace with your workload identity provider

      - name: 'Deploy to Cloud Run'
        uses: 'google-github-actions/deploy-cloudrun@33553064113a37d688aa6937bacbdc481580be17' # google-github-actions/deploy-cloudrun@v2
        with:
          service: '${{ env.SERVICE }}'
          region: '${{ env.REGION }}'
          # NOTE: If using a different source folder, update the image name below:
          source: './'

      # If required, use the Cloud Run URL output in later steps
      - name: 'Show output'
        run: |-
          echo ${{ steps.deploy.outputs.url }}
"""
    workflow, problems = parse_workflow_string(workflow_string)
    gen = rules.StepsIOMatch.check(workflow)
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], LintProblem)
    assert result[0].rule == 'steps_io_match'
    assert result[0].level == 'error'
    assert result[0].message == (
        "Can't find step 'deploy' in workflow"
    )
    assert result[0].line == 38