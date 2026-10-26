# Endpoint AI Discovery

Finds the AI agents installed on employee Macs and on Linux servers, and reports them to Arthur.
That covers coding agents with shell and filesystem access, autonomous local agents, personal
agents bridging chat platforms, and AI browsers and extensions. These tools install as npm
globals, Homebrew casks, browser extensions and config files, so an MDM's own software
inventory does not see them.

**New here? Start with the [quick start](docs/quickstart.md).**

## How it works

1. A scheduled script runs [osquery](https://osquery.io) and writes what it found to
   `/var/lib/arthur/`. The script is `dist/collect.sh` on macOS and `dist/collect-linux.sh`
   on Linux.
2. The platform that already manages the machine carries that file. On Jamf Pro it is Extension
   Attributes; on Compute Engine, guest attributes; on EC2, SSM custom inventory.
3. Arthur's collector reads the file through that platform's API and matches it against the
   agent catalog.

The machine lists everything it finds and matches nothing; only the collector matches. So when
a new agent is added to the catalog, Arthur finds it on machines that have already reported,
without a new scan.

Model runners, MCP libraries and container runtimes are not agents, so they are out of scope.

## What it collects

It collects names, paths, versions and declared permissions. It does not collect file
contents, secrets, browser history or cookies. It runs nothing it finds and changes nothing on
the machine.

It cannot see:

- inside a VM guest
- what a running container is doing
- containers in runtimes other than Docker, such as Podman
- which filesystem roots an MCP server exposes
- outbound destinations

## Docs

| Doc | Covers |
|---|---|
| [Quick start](docs/quickstart.md) | a first run on one machine, then a first deployment |
| [Jamf Pro](docs/mdm/jamf-pro.md), [Compute Engine](docs/mdm/gce.md), [EC2](docs/mdm/ec2.md) | deployment runbooks: prerequisites, rollout, reading the status, troubleshooting and rollback |
| [Architecture](docs/architecture.md) | how the parts fit together, the contracts between them, the measured limits, and why it is built this way |
| [Carrier requirements](docs/mdm/README.md) | what an MDM or cloud must provide to carry the payload |
| [Tests](test/README.md) | what each test guards against |

## Development

**This tree writes no osquery.** The queries and the runner are the osquery binding of
[ai-detection-spec](https://github.com/arthur-ai/ai-detection-spec), vendored under
`vendor/` at a pinned ref, so a query change is made upstream. This tree owns four
things:

- the build
- the `arthur1.` wire format
- the size budget
- the carriers

`test/lint.sh` fails if a second osquery implementation appears outside `vendor/`.

| Path | Contents |
|---|---|
| `vendor/ai-detection-spec/` | the queries and the runner at a pinned ref. **Do not edit**; re-vendor instead |
| `tools/vendor-queries.sh` | vendors upstream's osquery binding (`osquery/bin/`, `osquery/dist/`, the bundler) at one ref. The agent catalog and the matcher are vendored into ml-engine instead |
| `tools/build-collector.py` | builds `dist/collect.sh` and `dist/collect-linux.sh`, each one self-contained file |
| `dist/` | the built collectors. Generated, and committed so reviewers see them change |
| `deploy/` | the macOS LaunchDaemon; the systemd units, the Compute Engine and EC2 reporters, the Compute Engine OS policy and the EC2 CloudFormation template |
| `deploy/terraform/` | a Terraform module that deploys the OS policy across projects and zones, or through a policy orchestrator |
| `tools/render-os-policy.sh` | pins the OS policy to one ref of this repository, for gcloud |
| `deploy/arthur-ai-discovery.cfn.yaml` | the EC2 CloudFormation template, deployed as a stack per region or as an organization StackSet |
| `tools/render-cfn-template.sh` | pins that template to one ref of this repository |
| `test/` | lint, the collector run, the reporters against fake metadata servers, and the units under systemd |

```bash
tools/vendor-queries.sh <ref>     # vendor upstream at a ref; checks upstream's build first
tools/build-collector.py          # rebuild both collectors
test/lint.sh                      # static checks, ~1s
test/run-collector.sh             # run this platform's collector and check its output, ~15s
```

After a vendor bump, check what the new upstream version removed as well as what it added.
`test/lint.sh` fails if the collector passes `bin/discover` a flag it no longer accepts.
