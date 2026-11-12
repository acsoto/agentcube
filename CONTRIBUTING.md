# Contributing to AgentCube

Thank you for your interest in improving AgentCube! This guide outlines how to get started, the workflow we follow, and the expectations for contributors. The structure closely follows the [Volcano](https://github.com/volcano-sh/volcano/blob/master/contribute.md) contributor guide, with adjustments for the AgentCube project.

## Current Priorities and Contribution Scope

AgentCube currently prioritizes core capabilities, complete user workflows, and
demonstrated failures in supported usage. Maintainer review capacity is limited.
Before starting an implementation, obtain a maintainer's explicit agreement on
the problem and scope in an issue or discussion, or choose work a maintainer has
already marked `help wanted` or `good first issue`.

Unsolicited fixes for hypothetical corner cases, defensive hardening, and code
cleanup are generally outside the current scope unless a maintainer requests
them. A demonstrated bug may still be deferred or declined based on its impact,
maintenance cost, and current priorities. Patch size and passing tests alone do
not establish that a change should be accepted.

### Choose the Right Type

| Type | Use it for | What is needed before implementation |
| --- | --- | --- |
| Bug report (`kind/bug`) | An observed failure in supported usage, contrary to documented or agreed behavior | A real usage scenario, execution evidence, and maintainer agreement on scope |
| Feature request (`kind/feature`) | A missing capability or new user workflow | A concrete use case, expected outcome, and agreement on design and scope |
| Improvement proposal (`kind/enhancement`) | Changes to existing capabilities, including performance improvements or hardening | An actual need, expected benefit, and agreement that the work fits current priorities |
| Cleanup or refactoring (`kind/cleanup`) | Internal restructuring without changing user behavior | Maintainer-requested work or cleanup necessary for an accepted change; discuss standalone proposals first |
| Documentation (`kind/documentation`) | Incorrect or missing instructions or examples | The affected documentation, the correct behavior or missing workflow, and scope agreement |
| Question (`question`) | Help with setup, configuration, usage, or understanding behavior | Ask in Discussions; no implementation is implied |

Template labels classify submissions; they do not indicate maintainer acceptance.
Creating an issue or assigning it to yourself does not establish acceptance.
Maintainers set `help wanted` and `good first issue` after reviewing the task.
Changing a speculative bug report to an improvement proposal does not waive the
need to demonstrate value and agree on scope.

### Bug Report Evidence

Before reporting a bug, reproduce it by running AgentCube or the affected
component through a supported user-facing workflow. Include:

* The task you were performing, the observed impact, and the documented or agreed
  behavior you expected.
* The affected version or commit, environment, and relevant configuration.
* Minimal configuration, inputs, and exact commands or requests to reproduce the
  failure, together with actual and expected results.
* Actual execution output: relevant logs, events, error messages, traces, or
  screenshots/recordings where useful. Screenshots alone do not replace the
  reproduction steps. For intermittent failures, include the attempt count or
  duration and observed frequency; for performance claims, include measurements,
  workload scale, and how they were collected.

Cluster lifecycle and orchestration problems require reproduction with AgentCube
deployed in a Kubernetes cluster; kind or minikube is sufficient. SDK, CLI, and
standalone component problems may use a minimal runnable example exercising the
affected public interface in its supported environment.

Source-code inspection, static analysis, AI output, mocks, or a unit test alone
do not replace this execution evidence. A suggested root cause or fix is optional.
Regression tests are useful for validating an accepted fix, but must exercise the
reported behavior rather than merely assert the proposed implementation.
Maintainers are not responsible for constructing reproductions for speculative
findings. Report suspected security vulnerabilities privately through the
[security reporting channel](#security-reporting).

### Review Capacity and Submission Limits

Contributors without a merged code PR should have only one open code PR at a
time, unless a maintainer invites a coordinated series. Do not open batches of
speculative issues or PRs; wait for feedback on your current proposal before submitting more related work.
Keep each report concise and address review questions in your own words.

Maintainers may close submissions that lack required evidence, bypass scope
agreement, duplicate existing work, or fall outside current priorities without
performing a full code review or providing a point-by-point rebuttal. Closed
reports can be reconsidered when new evidence addresses the stated reason; do
not resubmit the same claim or patch under another category. Repeated disregard
of these rules or fabricated execution evidence may result in contribution
restrictions. These expectations apply regardless of the tools used.

## 👋 How to Get Involved

* Join the conversation on GitHub:
  * [Issues](https://github.com/volcano-sh/agentcube/issues) for bug reports and feature requests
  * [Discussions](https://github.com/volcano-sh/agentcube/discussions) for design questions and ideas
* Review the [code of conduct](https://github.com/volcano-sh/community/blob/master/CODE_OF_CONDUCT.md) before participating

##  Contribution Workflow

### 1. Pick or Propose Work

* Search open issues labeled `good first issue` or `help wanted`
* Use the appropriate issue form and follow the scope and evidence requirements above
* Discuss design questions and standalone cleanup proposals in Discussions first
* Wait for a maintainer to accept the problem and scope before submitting an implementation

### 2. Set Up Your Environment

* Install Go (version listed in `go.mod`)
* Clone the repository and ensure scripts in `Makefile` run locally:
  * `make lint`
  * `make test`
  * `make build`

### 3. Create a Working Branch

```bash
# from the repo root
git checkout main
git pull origin main
git checkout -b feat/<short-description>
```

### 4. Develop with Tests

* Follow Go best practices and respect existing module structure under `pkg/` and `cmd/`
* Maintain backwards compatibility for user-facing APIs (CRDs, CLI, HTTP schemas)
* Add unit tests in the relevant `*_test.go` files or integration tests under `test/`
* Run `make lint` and `make test` before submitting your changes

### 5. Commit Conventions

* Use clear, descriptive commit messages: `component: summary`
* Reference issues with `Fixes #<issue-number>` or `Refs #<issue-number>` when applicable
* Sign off your commits if required by your employer/company policies

### 6. Keep Your Branch Up to Date

* Rebase frequently on `main` to reduce merge conflicts:

```bash
git fetch origin
git rebase origin/main
```

* Resolve conflicts locally and rerun tests after rebasing

### 7. Open a Pull Request

* Push your branch and create a PR against `main`
* Fill in the PR template, covering:
  * Problem statement
  * Summary of changes
  * Testing performed
  * Screenshots/logs if relevant
* Link the accepted issue or discussion and the maintainer's scope agreement; a maintainer-created `help wanted` or `good first issue` task also qualifies
* Include reproduction evidence for bug fixes and the commands and actual results used to validate the change
* Request review from maintainers or area owners (see the `OWNERS` directories)

### 8. Code Review

To make it easier for your PR to receive reviews, consider the reviewers will need you to:

* follow [good coding guidelines](https://go.dev/wiki/CodeReviewComments).
* write [good commit messages](https://chris.beams.io/posts/git-commit/).
* break large changes into a logical series of smaller patches which individually make easily understandable changes, and in aggregate solve a broader issue.
* label PRs with appropriate reviewers: to do this read the messages the bot sends you to guide you through the PR process.

### 9. Address Review Feedback

* Be responsive to comments and iterate quickly
* Reply to each comment once addressed
* Squash commits if asked by reviewers to keep history clean

### 10. Celebrate the Merge 

* Once the PR is approved and checks are green, the maintainer will merge it
* Your contribution becomes part of the AgentCube history!

##  Coding Standards

* Follow Go gofmt formatting automatically (run make fmt)
* Maintain consistent log semantics via the shared logging packages under `pkg/`
* Keep public API changes backward compatible; update CRDs and generated clients when fields change (`make generate`)
* Document new features under `docs/` and update READMEs/examples when behavior changes

##  AI Guidance
Using AI tools to help write your PR is acceptable, but as the author, you are responsible for understanding every change. Do not leave the first review of AI generated changes to the reviewers, verify the changes (code review, testing, etc.) before submitting your PR. Reviewers may ask questions about your AI-assisted code, and if you cannot explain why a change was made, the PR will be closed. When responding to review comments, please do so without relying on AI tools. Reviewers want to engage directly with you, not with generated responses. If you used AI tools in preparing your PR, please disclose this in the "Special notes for your reviewer" section. All contributions must follow the contributions policies and use commit messages that align with the policy. Large AI generated PRs and AI generated commit messages are discouraged.

##  Testing Guidelines

* Unit tests are mandatory for new functionality and bug fixes
* Use table-driven tests where appropriate for clarity
* For concurrency-sensitive code, add race detector checks (`go test -race ./...`)
* Integration tests should target scenarios under `test/` or `example/`

##  Documentation Expectations

* Update relevant docs under `docs/`
* Provide getting-started examples if introducing new CRDs or CLI commands
* Refresh charts/examples under `example/` when changing deployments
* Include release notes summary for significant changes (tag `release-note`) in PRs

##  Governance and Ownership

* Maintainers are listed in the top-level [`OWNERS`](./OWNERS) file and `OWNERS` files in subdirectories
* Subsystem owners review and approve changes in their areas
* Major design decisions go through proposals in `docs/proposals/`. Existing
  historical design documents remain under `docs/design/` and are indexed from
  `docs/proposals/README.md`.

##  Tooling

* `make lint` runs linters (`golangci-lint`)
* `make test` runs unit tests
* `make e2e` runs the full E2E test suite
* `make build-all` produces component binaries (`workloadmanager`, `agentcube-router`) under `bin/`
* `make generate` regenerates codegen artifacts (CRDs, DeepCopy methods)
* `make gen-client` regenerates client-go code
* `make gen-all` regenerates all codegen artifacts

##  Security Reporting

* For sensitive issues, email volcano-security@googlegroups.com instead of filing a public issue
* Provide steps to reproduce, affected components, and impact assessment

##  License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License. See [LICENSE](./LICENSE) for details.
