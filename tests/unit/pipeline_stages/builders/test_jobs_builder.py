# flake8: noqa: E501

from tests.conftest import parse_workflow_string
from validate_actions.domain_model import ast, contexts


class TestJobsBuilder:
    def test_job_env(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          FIRST_NAME: Mona
          LAST_NAME: Octocat
        steps:
          - name: Checkout
            uses: actions/checkout@v4
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        env_ = workflow_out.jobs_["build"].env_
        assert problems.problems == []
        assert env_.get("GITHUB_TOKEN").string == "${{ secrets.GITHUB_TOKEN }}"
        assert env_.get("FIRST_NAME").string == "Mona"
        assert env_.get("LAST_NAME").string == "Octocat"


    # Integration tests for job-level defaults using parse_workflow_string


    def test_job_defaults_shell(self):
        workflow_string = """
    on: push
    jobs:
      build:
        defaults:
          run:
            shell: pwsh
        runs-on: ubuntu-latest
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        defaults = workflow_out.jobs_["build"].defaults_
        assert len(problems.problems) == 0
        assert defaults is not None
        assert defaults.shell_.value == "pwsh"
        assert defaults.working_directory_ is None


    def test_job_defaults_working_directory(self):
        workflow_string = """
    on: push
    jobs:
      build:
        defaults:
          run:
            working-directory: /home/user
        runs-on: ubuntu-latest
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        defaults = workflow_out.jobs_["build"].defaults_
        assert len(problems.problems) == 0
        assert defaults is not None
        assert defaults.shell_ is None
        assert defaults.working_directory_.string == "/home/user"


    def test_job_defaults_shell_and_working_directory(self):
        workflow_string = """
    on: push
    jobs:
      build:
        defaults:
          run:
            shell: sh
            working-directory: /tmp
        runs-on: ubuntu-latest
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        defaults = workflow_out.jobs_["build"].defaults_
        assert len(problems.problems) == 0
        assert defaults is not None
        assert defaults.shell_.value == "sh"
        assert defaults.working_directory_.string == "/tmp"


    def test_job_defaults_invalid_structure(self):
        workflow_string = """
    on: push
    jobs:
      build:
        defaults: not_a_map
        runs-on: ubuntu-latest
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        assert workflow_out.jobs_["build"].defaults_ is None
        assert any(p.desc.startswith("Invalid 'defaults:'") for p in problems.problems)


    def test_job_defaults_invalid_shell(self):
        workflow_string = """
    on: push
    jobs:
      build:
        defaults:
          run:
            shell: fish
        runs-on: ubuntu-latest
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        assert workflow_out.jobs_["build"].defaults_ is None
        assert any(p.desc == "Invalid shell: fish" for p in problems.problems)


    def test_job_permissions_single(self):
        workflow_string = """
    on: push
    jobs:
      stale:
        runs-on: ubuntu-latest

        permissions:
          issues: write
          pull-requests: read
          pull_request_review: none

        steps:
          - uses: actions/stale@v9
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        permissions_ = workflow_out.jobs_["stale"].permissions_
        assert problems.problems[0].desc == "Invalid permission: pull_request_review"
        assert permissions_.issues_ == ast.Permission.write
        assert permissions_.pull_requests_ == ast.Permission.read
        assert permissions_.id_token_ == ast.Permission.none
        assert permissions_.contents_ == ast.Permission.write


    def test_job_permissions_bulk(self):
        workflow_string = """
    on: push
    jobs:
      stale:
        runs-on: ubuntu-latest

        permissions: read-all

        steps:
          - uses: actions/stale@v9
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        permissions_ = workflow_out.jobs_["stale"].permissions_
        assert problems.problems == []
        assert permissions_.issues_ == ast.Permission.read
        assert permissions_.pull_requests_ == ast.Permission.read


    def test_job_permissions_none(self):
        workflow_string = """
    on: push
    jobs:
      stale:
        runs-on: ubuntu-latest

        permissions: {}

        steps:
          - uses: actions/stale@v9
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        permissions_ = workflow_out.jobs_["stale"].permissions_
        assert problems.problems == []
        assert permissions_.issues_ == ast.Permission.none
        assert permissions_.pull_requests_ == ast.Permission.none


    def test_jobs_context_builds(self):
        workflow_string = """
        on: push
        jobs:
          stale:
            runs-on: ubuntu-latest

            outputs:
              stale_output: ${{ steps.one.outputs.closed-issues-prs }}

            steps:
              - id: one
                uses: actions/stale@v9

        """  # TODO check if output reference is correct
        workflow_out, problems = parse_workflow_string(workflow_string)
        jobs_context = workflow_out.contexts.jobs
        assert isinstance(jobs_context, contexts.JobsContext)
        jobs_context_stale = jobs_context.children_["stale"]
        assert isinstance(jobs_context_stale, contexts.JobVarContext)
        jobs_context_stale_outputs = jobs_context_stale.outputs
        assert isinstance(jobs_context_stale_outputs, contexts.OutputsContext)
        stale_output = jobs_context_stale_outputs.children_["stale_output"]
        assert stale_output is not None
        assert isinstance(stale_output, contexts.ContextType)


    def test_job_context_builds(self):
        workflow_string = """
        on: push
        jobs:
          job:
            runs-on: ubuntu-latest
            services:
              nginx:
                image: nginx
                # Map port 8080 on the Docker host to port 80 on the nginx container
                ports:
                  - 8080:80
              redis:
                image: redis
                # Map random free TCP port on Docker host to port 6379 on redis container
                ports:
                  - 6379/tcp
            steps:
              - run: |
                  echo "Redis available on 127.0.0.1:${{ job.services.redis.ports['6379'] }}"
                  echo "Nginx available on 127.0.0.1:${{ job.services.nginx.ports['80'] }}"

        """
        workflow_out, problems = parse_workflow_string(workflow_string)
        job_context = workflow_out.jobs_["job"].contexts.job
        assert isinstance(job_context, contexts.JobContext)


    def test_strategy(self):
        workflow_string = """
        on: push
        jobs:
          example_matrix:
            strategy:
              matrix:
                os: [windows-latest, ubuntu-latest]
                node: [14, 16]
                include:
                  - os: windows-latest
                    node: 16
                    npm: 6
              fail-fast: true
              max-parallel: 6
            runs-on: ${{ matrix.os }}
            steps:
              - uses: actions/setup-node@v4
                with:
                  node-version: ${{ matrix.node }}
              - if: ${{ matrix.npm }}
                run: npm install -g npm@${{ matrix.npm }}
              - run: npm --version
        """
        workflow_out, problems = parse_workflow_string(workflow_string)
        assert problems.problems == []

        strategy = workflow_out.jobs_["example_matrix"].strategy_
        assert strategy is not None
        assert strategy.fail_fast_ is True
        assert strategy.max_parallel_ == 6

        # Expected combinations:
        # {os: windows-latest, node: 14}
        # {os: windows-latest, node: 16, npm: 6} (from include)
        # {os: ubuntu-latest, node: 14}
        # {os: ubuntu-latest, node: 16}

        combinations = strategy.combinations
        assert len(combinations) == 4

        expected_combinations = [
            {"os": "windows-latest", "node": "14"},
            {"os": "windows-latest", "node": "16", "npm": "6"},
            {"os": "ubuntu-latest", "node": "14"},
            {"os": "ubuntu-latest", "node": "16"},
        ]

        # Convert ast.String in combinations to simple dicts for easier comparison
        parsed_combinations = []
        for combo_dict in combinations:
            parsed_combo = {k.string: v.string for k, v in combo_dict.items()}
            parsed_combinations.append(parsed_combo)

        for expected_combo in expected_combinations:
            assert (
                expected_combo in parsed_combinations
            ), f"Expected combination {expected_combo} not found"

        # Check matrix context
        matrix_context = workflow_out.jobs_["example_matrix"].contexts.matrix
        assert matrix_context is not None
        assert "os" in matrix_context.children_
        assert "node" in matrix_context.children_
        assert "npm" in matrix_context.children_
        assert matrix_context.children_["os"] == contexts.ContextType.string
        assert matrix_context.children_["node"] == contexts.ContextType.string
        assert matrix_context.children_["npm"] == contexts.ContextType.string


    def test_job_runs_on_mapping_scalar_items(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on:
          labels: ubuntu-latest
          group: my-group
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        runs_on = workflow_out.jobs_["build"].runs_on_
        assert problems.problems == []
        assert [l.string for l in runs_on.labels] == ["ubuntu-latest"]
        assert [g.string for g in runs_on.group] == ["my-group"]


    def test_job_runs_on_single(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        runs_on = workflow_out.jobs_["build"].runs_on_
        assert problems.problems == []
        assert [l.string for l in runs_on.labels] == ["ubuntu-latest"]


    def test_job_runs_on_list(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on: [ubuntu-latest, windows-latest]
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        runs_on = workflow_out.jobs_["build"].runs_on_
        assert problems.problems == []
        assert [l.string for l in runs_on.labels] == ["ubuntu-latest", "windows-latest"]


    def test_job_runs_on_unknown_key(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on:
          foo: bar
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        runs_on = workflow_out.jobs_["build"].runs_on_
        assert runs_on is not None
        # Unknown key should produce an error but still return RunsOn
        assert any(p.desc == "Unknown key in 'runs-on': foo" for p in problems.problems)
        assert runs_on.labels == []
        assert runs_on.group == []


    def test_job_runs_on_mapping_list_with_invalid_items(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on:
          labels: [ubuntu-latest, 123, windows-latest]
          group: true
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        runs_on = workflow_out.jobs_["build"].runs_on_
        # Two errors: one for invalid list item 123, one for invalid scalar for group
        assert len(problems.problems) == 2
        descs = [p.desc for p in problems.problems]
        assert "Invalid item in 'runs-on' 'labels': 123" in descs
        assert "Invalid item in 'runs-on' 'group': True" in descs


    def test_job_environment_string(self):
        workflow_string = """
    on: push
    jobs:
      deploy:
        runs-on: ubuntu-latest
        environment: production
        steps:
          - name: Do something
            run: echo done
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        environment = workflow_out.jobs_["deploy"].environment_
        assert problems.problems == []
        assert environment is not None
        assert environment.name_.string == "production"
        assert environment.url_ is None


    def test_job_environment_mapping(self):
        workflow_string = """
    on: push
    jobs:
      deploy:
        runs-on: ubuntu-latest
        environment:
          name: staging
          url: https://example.com
        steps:
          - name: Do something
            run: echo done
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        environment = workflow_out.jobs_["deploy"].environment_
        assert problems.problems == []
        assert environment is not None
        assert environment.name_.string == "staging"
        assert environment.url_.string == "https://example.com"


    def test_job_environment_invalid_scalar(self):
        workflow_string = """
    on: push
    jobs:
      deploy:
        runs-on: ubuntu-latest
        environment: 123
        steps:
          - name: Do something
            run: echo done
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        assert workflow_out.jobs_["deploy"].environment_ is None
        assert len(problems.problems) == 1
        descs = [p.desc for p in problems.problems]
        assert "Invalid 'environment' value: '123'" in descs


    def test_job_environment_invalid_name_mapping(self):
        workflow_string = """
    on: push
    jobs:
      deploy:
        runs-on: ubuntu-latest
        environment:
          name: 123
          url: https://example.com
        steps:
          - name: Do something
            run: echo done
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        assert workflow_out.jobs_["deploy"].environment_ is None
        descs = [p.desc for p in problems.problems]
        assert "Invalid 'environment' 'name': '123'" in descs


    def test_job_environment_invalid_url_mapping(self):
        workflow_string = """
    on: push
    jobs:
      deploy:
        runs-on: ubuntu-latest
        environment:
          name: staging
          url: 456
        steps:
          - name: Do something
            run: echo done
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        assert workflow_out.jobs_["deploy"].environment_ is None
        descs = [p.desc for p in problems.problems]
        assert "Invalid 'environment' 'url': '456'" in descs


    def test_job_concurrency_minimal_group(self):
        workflow_string = """
    on: push
    jobs:
      job1:
        concurrency:
          group: job-group
        runs-on: ubuntu-latest
        steps:
          - name: Test
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        job = workflow_out.jobs_["job1"]
        assert len(problems.problems) == 0
        assert job.concurrency_ is not None
        assert job.concurrency_.group_.string == "job-group"
        assert job.concurrency_.cancel_in_progress_ is None


    def test_job_concurrency_with_cancel_true(self):
        workflow_string = """
    on: push
    jobs:
      job2:
        concurrency:
          group: job2-group
          cancel-in-progress: true
        runs-on: ubuntu-latest
        steps:
          - name: Test
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        job = workflow_out.jobs_["job2"]
        assert len(problems.problems) == 0
        assert job.concurrency_ is not None
        assert job.concurrency_.group_.string == "job2-group"
        assert job.concurrency_.cancel_in_progress_ is True


    def test_job_concurrency_missing_group(self):
        workflow_string = """
    on: push
    jobs:
      job3:
        concurrency:
          cancel-in-progress: true
        runs-on: ubuntu-latest
        steps:
          - name: Test
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        job = workflow_out.jobs_["job3"]
        assert job.concurrency_ is None
        assert any(p.desc == "Concurrency must define 'group'" for p in problems.problems)


    def test_job_container_simple(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        container: node:16-bullseye
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        container = workflow_out.jobs_["build"].container_
        assert problems.problems == []
        assert container is not None
        assert str(container.image_) == "node:16-bullseye"


    def test_job_container_full(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        container:
          image: node:16-bullseye
          credentials:
            username: octocat
            password: password
          env:
            NODE_ENV: development
          ports:
            - 8080:80
          volumes:
            - my_docker_volume:/volume_mount
          options: --cpus 1
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        container = workflow_out.jobs_["build"].container_
        assert problems.problems == []
        assert container is not None
        assert container.image_.string == "node:16-bullseye"
        assert container.credentials_ is not None
        assert container.credentials_.username_.string == "octocat"
        assert container.credentials_.password_.string == "password"
        assert container.env_ is not None
        assert container.env_.get("NODE_ENV").string == "development"
        assert container.ports_ is not None
        assert [p.string for p in container.ports_] == ["8080:80"]
        assert container.volumes_ is not None
        assert [v.string for v in container.volumes_] == ["my_docker_volume:/volume_mount"]
        assert container.options_.string == "--cpus 1"


    def test_job_container_invalid_structure(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        container: [ "node:16-bullseye" ]
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        container = workflow_out.jobs_["build"].container_
        assert container is None
        assert len(problems.problems) == 1
        assert problems.problems[0].desc == "Container must be a string or a mapping."


    def test_job_container_missing_image(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        container:
          credentials:
            username: octocat
            password: password
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        container = workflow_out.jobs_["build"].container_
        assert container is None
        assert len(problems.problems) == 1
        assert problems.problems[0].desc == "Container must have an 'image' property."


    def test_job_container_invalid_credentials(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        container:
          image: node:16-bullseye
          credentials:
            username: octocat
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        container = workflow_out.jobs_["build"].container_
        assert container is not None
        assert container.credentials_ is None
        assert len(problems.problems) == 1
        assert (
            problems.problems[0].desc == "Container credentials must have 'username' and 'password'."
        )


    def test_job_container_invalid_ports(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        container:
          image: node:16-bullseye
          ports:
            - 80
            - "8080:80"
            - {}
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        container = workflow_out.jobs_["build"].container_
        assert container is not None
        assert container.ports_ is None
        assert len(problems.problems) == 1
        assert "Container ports must be a list of strings." in problems.problems[0].desc


    def test_job_container_invalid_volumes(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        container:
          image: node:16-bullseye
          volumes:
            - my_docker_volume:/volume_mount
            - 123
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        container = workflow_out.jobs_["build"].container_
        assert container is not None
        assert container.volumes_ is None
        assert len(problems.problems) == 1
        assert "Container volumes must be a list of strings." in problems.problems[0].desc


    def test_job_container_invalid_options(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        container:
          image: node:16-bullseye
          options: ["--cpus 1"]
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        container = workflow_out.jobs_["build"].container_
        assert container is not None
        assert container.options_ is None
        assert len(problems.problems) == 1
        assert problems.problems[0].desc == "Container options must be a string."


    def test_job_container_unknown_key(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        container:
          image: node:16-bullseye
          foo: bar
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        container = workflow_out.jobs_["build"].container_
        assert container is not None
        assert len(problems.problems) == 1
        assert problems.problems[0].desc == "Unknown container key: foo"


    def test_job_container_multiple_options_in_string(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        container:
          image: node:16-bullseye
          options: --cpus 1 --memory 1024m
        steps:
          - name: Echo
            run: echo hi
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        container = workflow_out.jobs_["build"].container_
        assert problems.problems == []
        assert container is not None
        assert container.options_.string == "--cpus 1 --memory 1024m"


    def test_job_with_uses_and_with(self):
        workflow_string = """
    on: push
    jobs:
      reusable_job:
        uses: ./.github/workflows/reusable-workflow.yml
        with:
          username: mona
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        job = workflow_out.jobs_["reusable_job"]
        assert problems.problems == []
        assert job.uses_.string == "./.github/workflows/reusable-workflow.yml"
        assert job.with_["username"].string == "mona"


    def test_job_with_invalid_uses(self):
        workflow_string = """
    on: push
    jobs:
      reusable_job:
        uses: 123
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        assert len(problems.problems) == 1
        assert "Invalid 'uses' value, it must be a string." in problems.problems[0].desc


    def test_job_with_invalid_with(self):
        workflow_string = """
    on: push
    jobs:
      reusable_job:
        uses: ./.github/workflows/reusable-workflow.yml
        with: "hello"
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        assert len(problems.problems) == 1
        assert "Invalid 'with' value: must be a mapping." in problems.problems[0].desc


    def test_job_secrets_map(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        secrets:
          my_secret: ${{ secrets.REPO_SECRET }}
          gh_token: ${{ secrets.GITHUB_TOKEN }}
        steps:
          - name: Checkout
            uses: actions/checkout@v4
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        secrets_ = workflow_out.jobs_["build"].secrets_
        assert problems.problems == []
        assert secrets_ is not None
        assert secrets_.inherit is False
        assert secrets_.secrets["my_secret"].string == "${{ secrets.REPO_SECRET }}"
        assert secrets_.secrets["gh_token"].string == "${{ secrets.GITHUB_TOKEN }}"


    def test_job_secrets_inherit(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        secrets: inherit
        steps:
          - name: Checkout
            uses: actions/checkout@v4
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        secrets_ = workflow_out.jobs_["build"].secrets_
        assert problems.problems == []
        assert secrets_ is not None
        assert secrets_.inherit is True
        assert secrets_.secrets == {}


    def test_job_secrets_invalid_value(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        secrets: 123
        steps:
          - name: Checkout
            uses: actions/checkout@v4
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        assert workflow_out.jobs_["build"].secrets_ is None
        assert len(problems.problems) == 1
        assert "Invalid 'secrets' value: must be a mapping or 'inherit'." in problems.problems[0].desc


    def test_job_secrets_invalid_mapping_value(self):
        workflow_string = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        secrets:
          my_secret: [1, 2, 3]
        steps:
          - name: Checkout
            uses: actions/checkout@v4
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        secrets_ = workflow_out.jobs_["build"].secrets_
        assert secrets_ is not None
        assert len(problems.problems) == 1
        assert "Each secret value must be a string." in problems.problems[0].desc


    def test_jobs_output_accessible_at_workflow_level(self):
        """Test that jobs.<jobid>.outputs.<output_name> is accessible at workflow level."""
        workflow_string = """
    name: Reusable workflow

    on:
      workflow_call:
        outputs:
          firstword:
            description: "The first output string"
            value: ${{ jobs.example_job.outputs.output1 }}
          secondword:
            description: "The second output string"
            value: ${{ jobs.example_job.outputs.output2 }}

    jobs:
      example_job:
        name: Generate output
        runs-on: ubuntu-latest
        outputs:
          output1: ${{ steps.step1.outputs.ref }}
          output2: ${{ steps.step2.outputs.ref }}
        steps:
          - id: step1
            uses: actions/checkout@v4
          - id: step2
            uses: actions/checkout@v4
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        assert problems.problems == []

        # Verify jobs context is available at workflow level
        jobs_context = workflow_out.contexts.jobs
        assert jobs_context is not None
        assert isinstance(jobs_context, contexts.JobsContext)

        # Verify example_job has the outputs in the context
        job_context = jobs_context.children_["example_job"]
        assert isinstance(job_context, contexts.JobVarContext)
        assert "output1" in job_context.outputs.children_
        assert "output2" in job_context.outputs.children_
        assert job_context.outputs.children_["output1"] == contexts.ContextType.string
        assert job_context.outputs.children_["output2"] == contexts.ContextType.string


    def test_jobs_output_not_accessible_within_job(self):
        """Test that jobs.<jobid>.outputs.<output_name> is NOT accessible within any job."""
        workflow_string = """
    on: push
    jobs:
      job1:
        runs-on: ubuntu-latest
        outputs:
          my_output: ${{ steps.step1.outputs.value }}
        steps:
          - id: step1
            run: echo "value=hello" >> $GITHUB_OUTPUT
      job2:
        runs-on: ubuntu-latest
        needs: job1
        steps:
          - run: echo "The output from job1 is ${{ jobs.job1.outputs.my_output }}"
    """
        workflow_out, problems = parse_workflow_string(workflow_string)
        assert problems.problems == []

        # Verify jobs context is NOT available within individual jobs
        job1 = workflow_out.jobs_["job1"]
        assert job1.contexts.jobs is None

        job2 = workflow_out.jobs_["job2"]
        assert job2.contexts.jobs is None
