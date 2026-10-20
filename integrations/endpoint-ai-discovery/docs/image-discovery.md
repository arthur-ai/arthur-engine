# AI discovery on Cloud Run and ECS: the image is the disk

A design, not a runbook. Nothing here is built; the sections say what is decided, what each
platform and registry gives, measured against their documentation, and what has to be measured
on a real account before the first line is written.

**The shape.** On a VM, the collector runs inside the machine and the management plane carries
what it wrote ([`architecture.md`](architecture.md)). Cloud Run and Fargate have no machine to
run anything in and no disk to snapshot: the root filesystem is the container image, plus a
writable layer that dies with the instance. But the control plane records which image digest
each revision or task runs, the digest names immutable bytes in a registry the governance
account can read, and a registry is read with an API call. So the scan does what a VM scan does
with the roster and the carrier swapped:

```
  Cloud Run Admin API / ECS API ──► revisions and tasks, each with an image digest
                                          │
                                          ▼
  Artifact Registry / ECR / any OCI registry ──► manifest, config, layers, by digest
                                          │  pulled into a scratch directory, never run
                                          ▼
  the image enumerator ──► the same six-column rows a Linux collector writes
                                          │
                                          ▼
  the collector ──► matching against the catalog, records per workload, coverage per workload
```

**Nothing of ours executes in the customer's environment.** The image is pulled and unpacked;
it is never started, not even with the entrypoint replaced. That is the same line the EC2
design drew when it rejected `ssm:SendCommand`.

**Why this is a better footing than a VM.** A VM's owner controls everything inside the guest
and can turn the agent off. A Cloud Run or ECS owner controls the image, but the control plane,
not the owner, records which digest runs, and an image in a registry cannot be edited in place:
a digest is a hash of the bytes. There is no agent to disable and no metadata key to flip. What
the owner can still do is install at startup (section 06), and that is the gap this design
names rather than closes.

## 00 · What each platform has instead of a disk

| | Root filesystem | Writable state | Snapshot | What records the digest |
|---|---|---|---|---|
| Cloud Run services, jobs, worker pools, functions | the image | memory-backed, lost with the instance; Cloud Storage, NFS or in-memory volumes by configuration | none | the revision, section 01 |
| ECS on Fargate | the image | task ephemeral storage, 20 GiB by default, gone with the task | none | the task, section 02 |
| ECS on EC2 | the host's EBS volume holds the Docker layer store | the host's | yes | the task, and the host is a VM: [`mdm/ec2.md`](mdm/ec2.md)'s collector sees its containers through the Docker socket |
| GKE, EKS | the image per pod; the node is a VM | | nodes, yes | the pod spec's `imageID`; not in this design, same answer |

ECS on EC2 is already covered twice: the host runs the VM collector, whose `containers` branch
lists what Docker holds, and this design reads the task's image as well. The two agree or they
are a finding.

## 01 · Cloud Run: where the digest is

A revision is immutable once created, and Cloud Run resolves the image reference to a digest
**when the revision is created**, whether the deploy named a tag or a digest. The Admin API
serves it two ways:

| API | Field | Notes |
|---|---|---|
| v2, `projects.locations.services.revisions.get` | `containerStatuses[].imageDigest`, output only, one per container | sidecars included |
| v1 (Knative shape), `namespaces.revisions.get` | `status.imageDigest` | one container per revision in v1 |

Google's reference for `ContainerStatus`: *"ImageDigest holds the resolved digest for the image
specified and resolved during the creation of Revision. This field holds the digest value
regardless of whether a tag or digest was originally specified in the Container object."*

The roster is `services.list` in each region of each project, then each service's revisions
that carry traffic, read from the service's `traffic` and `trafficStatuses`. A revision with no
traffic is kept in the roster and reported as such: it can be routed to with one command, so it
is not gone, and it is read once per digest anyway.

**Jobs are the gap on this platform.** A job's execution carries `template.containers[].image`
as it was written, and the Execution resource has no digest field at all, measured against the
v2 reference. For a job whose image is pinned by digest in the template, the digest is in the
reference. For one pinned by tag, the scan resolves the tag at the registry at scan time and
marks the record `digest=resolved-at-scan`: the tag may have moved since the execution ran, so
the row is evidence about what the job *would* run now, not what it ran. A job that has never
executed is reported but not read.

Functions are Cloud Run services whose image Cloud Build produced into Artifact Registry, so
they take the service path. Worker pools take it too.

Identity and address, in the terms the record contract uses:

| | Value |
|---|---|
| `device_key` | the revision's `uid` (a UUID the API assigns), never the revision name, which is reused by redeploys of a deleted service |
| `name` | `service/revision` |
| `address_scope` | `project/region` |
| `runs_on` | `GCP` |
| `platform` | `LINUX`; Cloud Run runs Linux containers only |

Permissions: `roles/run.viewer` holds `run.services.list`, `run.revisions.list`,
`run.revisions.get`, `run.jobs.list` and `run.executions.list`. **`run.revisions.get` returns
environment variable values in clear.** Section 05 says what is kept from that answer; the
permission cannot be narrowed below it.

## 02 · ECS: where the digest is

ECS resolves the image tag in a task definition to a digest **at deployment**, so that every
task of a service runs identical bytes; AWS calls this version consistency. `DescribeTasks`
serves the result per container as `containers[].imageDigest`, *"the container image manifest
digest"*, beside `image` as the task definition named it.

What AWS documents about when that field is empty, and so what the reader has to handle:

- The first task a service starts establishes the digests; a service with a desired count of
  zero has none until it next deploys.
- If establishing the digest fails three times, the deployment proceeds **without** digest
  resolution. `versionConsistency` in the container definition turns this off per container.
- ECS agent 1.31.0 to 1.69.0 resolved digests only for ECR images; 1.70.0 resolves any
  registry. Fargate Linux platform 1.3.0 or later does. A task on an older agent has no digest.
- Sidecars ECS manages itself, such as the GuardDuty agent and the Service Connect proxy, get
  no digest.

A task without a digest is read by resolving its task definition's `image` at the registry at
scan time, marked `digest=resolved-at-scan` as for a Cloud Run job, and counted
`digest-unresolved-by-platform` so a fleet of old agents shows as what it is.

The roster is `ListClusters`, `ListServices` and `ListTasks` per cluster, `DescribeTasks` in
pages of 100, and `DescribeTaskDefinition` once per task definition revision, in each region of
each account. Stopped tasks are read for their digest for as long as ECS lists them, about an
hour, and reported as stopped, as a stopped VM is.

| | Value |
|---|---|
| `device_key` | the task ARN; a relaunched task gets a new one |
| `name` | `cluster/service/task-definition:revision`, with the container name when a task has several |
| `address_scope` | `account/region` |
| `runs_on` | `AWS` |
| `platform` | `LINUX` for `operatingSystemFamily` LINUX; Windows tasks are counted `unsupported-platform` as Windows instances are |

Permissions: `ecs:ListClusters`, `ecs:ListServices`, `ecs:ListTasks`, `ecs:DescribeTasks`,
`ecs:DescribeTaskDefinition`, none scopable below `*`. **`DescribeTaskDefinition` returns
environment variable values in clear**, as Cloud Run's revision does; section 05.

## 03 · Registries: what the digest buys, per registry

Every registry below speaks the [OCI distribution API](https://github.com/opencontainers/distribution-spec/blob/main/spec.md),
which is what makes one reader serve all of them:

| Call | Gives |
|---|---|
| `HEAD /v2/<name>/manifests/<tag-or-digest>` | `Docker-Content-Digest`, the digest the tag resolves to now, without a pull. Counts toward no registry's pull limit that documents one |
| `GET /v2/<name>/manifests/<digest>` with an `Accept` naming both image manifests and image indexes | the manifest, or an index of per-platform manifests. The spec: *"clients SHOULD verify the returned manifest matches this digest"*, and the reader does |
| `GET /v2/<name>/blobs/<config digest>` | the image config: `config.Env`, `Entrypoint`, `Cmd`, `User`, `WorkingDir`, and `history[].created_by`, the Dockerfile lines that built each layer |
| `GET /v2/<name>/blobs/<layer digest>` | each layer, a tar, usually gzip or zstd, applied in order with whiteouts to make the filesystem |

**A digest can name an index, not an image.** A multi-architecture tag resolves to an image
index whose digest differs from every per-platform manifest's. Which of the two a control plane
reports is **not settled by either vendor's documentation**: ECS says "manifest digest", Cloud
Run says "resolved digest". The reader handles both, choosing the `linux/amd64` manifest from
an index, or `linux/arm64` for an ECS task whose task definition says so, and section 08 lists
the measurement that settles it.

### Artifact Registry

`projects.locations.repositories.dockerImages.list` returns one `DockerImage` per digest:

| Field | Carries |
|---|---|
| `name`, `uri` | end in `<image>@sha256:<64 hex>`; `uri` is the pullable reference |
| `tags` | the tags on that digest now, up to 100 |
| `uploadTime`, `buildTime`, `updateTime` | when it arrived, when it says it was built, when its tags last changed |
| `mediaType` | manifest or index |
| `imageManifests[]` | for an index, each per-platform manifest's `digest`, `architecture`, `os` |
| `imageSizeBytes` | what a pull will cost |

That listing needs `artifactregistry.dockerImages.list`; the pull needs
`artifactregistry.repositories.downloadArtifacts`, both in `roles/artifactregistry.reader`.
The legacy `gcr.io` hosts are served by Artifact Registry now and answer the same way.

**Artifact Analysis is the cheap first pass.** For an image in Artifact Registry that the
Container Scanning API has assessed, Google keeps a Grafeas `PACKAGE` occurrence per installed
package, OS and language packages alike, and an SBOM reference occurrence pointing at an SPDX
file in Cloud Storage. `containeranalysis.occurrences.list` (Container Analysis Occurrences
Viewer) answers "which images hold package X" without a pull. It covers only images the
scanner has seen, which is Artifact Registry images with scanning enabled, and it lists
packages, not files: an agent installed as `npm install -g` shows, a `~/.claude` directory does
not.

### Amazon ECR

`DescribeImages` returns one `ImageDetail` per manifest or index:

| Field | Carries |
|---|---|
| `imageDigest` | *"the sha256 digest of the image manifest"*; for an index, the index's digest. The per-platform manifests of an index are listed too, untagged |
| `imageTags` | the tags on it now |
| `imagePushedAt` | when it arrived |
| `lastRecordedPullTime` | when it was last pulled, refreshed at least every 24 hours, so a digest no task runs but something still pulls is visible |
| `imageManifestMediaType`, `artifactMediaType` | manifest or index, and what kind of artifact |
| `imageSizeInBytes` | for an index, the largest manifest's size |
| `imageScanStatus`, `imageScanFindingsSummary` | whether the registry's own scanner has seen it |
| `imageStatus` | `ACTIVE`, or `ARCHIVED` in ECR archive, which cannot be pulled until restored |

The pull is `GetAuthorizationToken`, then the distribution API against
`<account>.dkr.ecr.<region>.amazonaws.com`, which needs `ecr:BatchGetImage`,
`ecr:GetDownloadUrlForLayer` and `ecr:BatchCheckLayerAvailability`; `ecr:DescribeImages` for the
listing. A repository can be set to immutable tags; one that is not has tags that move, which is
why the control plane's digest, not the tag, is what is read.

**Inspector is ECR's first pass.** With enhanced scanning on, Amazon Inspector holds a package
inventory per image, OS and language packages, and `inspector2:CreateSbomExport` writes it as
CycloneDX 1.4 or SPDX 2.3 JSON to an S3 bucket, filtered by repository and tag. Basic scanning
covers OS packages only. The same limit as Google's: packages, not files, and only images the
scanner has seen.

### Docker Hub, GHCR, and everything else

A task definition or a Cloud Run container may name an image outside the account's own
registry. `registry-1.docker.io` and `ghcr.io` speak the distribution API with a bearer token
from their token endpoints, anonymous for public images. Docker Hub's documented limits are 100
pulls per six hours per IPv4 address unauthenticated and 200 for a personal account, where a
pull is up to two `GET`s on manifests and **`HEAD` requests are not counted**, so resolving
tags is free and pulls are what to budget. Neither offers the account's scanner data; every
such image is a full read.

Harbor, JFrog Artifactory, Quay, Nexus and GitLab's registry speak the same API, so a source
field naming a registry host and a credential is enough to read them. Their scanners are out of
scope; the full read is the floor.

## 04 · The image enumerator

**It enumerates; the collector matches.** The rule that decides the rest of this tree
([`architecture.md`](architecture.md)) holds here with one difference: there is no endpoint,
so the enumerator runs in the engine, in the same job as the matcher. The boundary stays a
code boundary, one module that walks a filesystem and writes rows, and one that reads rows and
the catalog, because the property the boundary buys is the same: a new signature re-matches
against what the enumerator already found, and nothing on the enumeration side knows what an
agent is.

What it walks, on the filesystem the layers make, as branches that name themselves in a
`kind=scan` row the way the Linux collector's do:

| Branch | Looks at | Static-only note |
|---|---|---|
| `packages-linux` | `/var/lib/dpkg/status`, the rpm database, `/lib/apk/db/installed` | the files, not the tools |
| `npm` | every `node_modules/*/package.json`, global and local; `/usr/local/lib/node_modules` | |
| `pip` | every `*.dist-info/METADATA` and `*.egg-info` under any `site-packages` or `dist-packages` | |
| `binaries` | the directories `config.Env`'s `PATH` names, and `/usr/local/bin` | name and size; no execution |
| `filesystem-linux` | dotdirs and config files under `/root`, `/home/*`, `WorkingDir` | the same paths the Linux queries glob |
| `systemd` | unit files under `/etc/systemd`, `/lib/systemd` | present in some images; never active |
| `history` | `history[].created_by` from the config: the `RUN` lines | the only trace of a `pip install` whose result is in the layer, and of a `curl | sh` whose result is not |
| `config` | `Entrypoint`, `Cmd`, `User`, and the **names** of `config.Env` | values dropped before anything is written |
| `running`, `ports`, `runtime-linux`, `containers` | nothing | `absent`: no process exists. Said in the scan row rather than left out |

Each branch ends in a dated `kind=scan` row saying `ok`, `absent` or why it could not look, so
an image with nothing in it reads as "looked, nothing there" and never as an empty value.

**It does not reuse the osquery queries, and it does not copy them.** osquery runs against a
live OS; an unpacked image is a directory. The paths the `filesystem-linux` and package branches
glob are the same ones, and the way to keep them the same is the catalog: signatures live in
`catalog/agents.yaml` upstream, and the enumerator, like the queries, reads none of them. What
the two implementations share is the row contract and the scan vocabulary, which `test/lint.sh`
already holds the Linux collector to. The enumerator belongs upstream, beside the queries, as a
second enumerator over the same catalog, so that a path added to a query is added where the
image walker will see it; this tree vendors it as it vendors the queries.

**Layers are extracted, never executed**, with whiteouts applied, symlinks resolved inside the
tree only, hard-link and path-traversal entries refused, and a size ceiling on the unpacked tree
that fails the read loudly as `image-too-large` rather than walking half of it. Pulling a
layer is a read; nothing is written back to any registry.

**The rows are framed and budgeted as a VM's are.** The same `arthur1.` frame and the same
256 KB budget, not because anything carries them, but so that one record pipeline reads every
source and one `ERROR:oversize:<bytes>` means the same thing everywhere.

## 05 · What leaves the registry and what does not

Identifiers and structure only. In particular:

- **Environment variable values are never read into a row**, from the image config, the Cloud
  Run revision or the ECS task definition. Names are: `ANTHROPIC_API_KEY` as a name is evidence
  of an AI client; its value is a credential. Secret *references* (Secret Manager, Secrets
  Manager, SSM Parameter Store ARNs) are kept by name.
- **File contents are never read**, except package manifests and the package databases, whose
  shape the branch knows. A `~/.claude/settings.json` is reported as present, with its size,
  not its contents.
- **Layers are deleted after the walk**, and the scratch directory is private to the job.
- Registry credentials and the control-plane credential are source secrets, scrubbed from the
  job log by the existing redaction.

## 06 · What it misses, said plainly

| Gap | Why | What covers it |
|---|---|---|
| Installs at startup | `pip install` or `curl \| sh` in an entrypoint puts the agent in the running container, not in any layer | the `history` and `config` branches show the install command, so the intent is a finding even when the result is not |
| Images outside the account's registries | pullable, but no scanner has seen them, and public registries rate-limit pulls | the full read, budgeted; section 03 |
| What the container talked to | nothing on disk says it | a network-signal source: DNS and flow logs to AI API endpoints, a separate design |
| Cloud Run jobs by tag, ECS tasks without a platform digest | the platform recorded no digest | resolved at scan time and marked as such; counted, never silently promoted to a fact |
| A revision replaced between roster and read | the digest is immutable, so the read is right about that digest; the roster says which digest was live when | the record is dated by the roster's read of the control plane, as a VM's is by its status line |

## 07 · Coverage, as per-workload entries

Every workload the roster lists is counted, decoded or not, and every one not decoded is listed
with its reason, as the VM sources list machines. The reasons this source adds:

| Reason | Meaning |
|---|---|
| `digest-unresolved-by-platform` | the control plane recorded no digest (section 02's cases); the image was resolved at scan time |
| `image-not-found` | the registry answers 404 for the digest: deleted, or in ECR archive |
| `registry-denied` | the registry refused the pull; the whole repository is likely denied, so this is also a denied scope |
| `unsupported-media-type` | not an OCI or Docker v2 image: a Helm chart, an attestation, a Windows image |
| `image-too-large` | the unpacked tree passed the ceiling |
| `layer-unreadable` | a layer failed its digest check or would not unpack |

A project, region, account or cluster that cannot be listed is a denied scope, reported on the
run as the organization-scoped VM sources report theirs, and a scan whose every scope was
denied fails rather than reporting a clean estate.

## 08 · What to measure before building

Each of these is a fact the code will depend on and the documentation does not settle:

1. **Which digest the control plane reports for a multi-architecture tag**: the index's or the
   platform manifest's. Deploy one `linux/amd64,linux/arm64` tag to a Cloud Run service and an
   ECS service, and compare `imageDigest` with `docker buildx imagetools inspect`.
2. **Whether `imageDigest` on a Fargate task survives a task definition update that keeps the
   same tag**, and what a task with `versionConsistency: disabled` reports.
3. **Cloud Run jobs**: whether any field anywhere on an execution or its tasks carries the
   pulled digest; the v2 Execution reference lists none.
4. **Artifact Analysis coverage of npm and pip packages installed outside the distribution's
   package manager**, which is where coding agents land. If it lists `/usr/local/lib/node_modules`
   the first pass is worth more than this design assumes.
5. **Unpack size and time** for a real service image, as the VM runbooks measured payloads:
   a Python service image, a Node image, and a distroless one. The size ceiling is set from
   that, not guessed.
6. **ECS sidecars**: that a task with a Service Connect proxy reports the application
   container's digest and omits the proxy's, as documented.

## 09 · Decisions

| Decision | Why |
|---|---|
| The image is read from the registry, never from a running instance | there is no disk and no agent on either platform, and a registry read executes nothing in the customer's environment |
| The control plane's digest is the identity of what runs; a tag is never trusted | tags move; the digest is a hash of the bytes, and both platforms record it at deploy |
| Resolved-at-scan digests are marked, and counted | a row that quietly reported a moved tag's bytes as what ran would be the silent wrong answer this tree exists to prevent |
| The enumerator is a second enumerator upstream, not a reuse of the queries and not a copy | osquery needs a live OS; a copy of the paths drifts, which is the failure the one-implementation rule records |
| Registry scanner data is a first pass, not the source of truth | it lists packages only, for images it has seen, and misses files; the full read is the floor |
| Environment variable values are dropped before any row exists | the permissions that reach the digest also reach the values, and a value is a credential |
| Per-workload coverage entries and denied scopes from the first version | the unobservable set is the finding a shadow AI program needs most, as it is on VMs |
| Network signals are a separate design | they answer a different question, usage rather than presence, and need a different roster |

## 10 · Open questions

- **Where rows live between scans.** A digest is immutable, so its rows never change; today
  they would be regenerated by re-pulling on every scan, which is correct and costs a pull per
  digest per scan. A per-digest cache on the engine's disk is the obvious optimization and
  carries no new trust; a cache on the Platform would mean the Platform receiving raw rows,
  which the architecture rules out.
- **One source or three.** `gcp_cloud_run` and `aws_ecs` as sources in the Cloud class, each
  reading its own control plane and whatever registries its workloads name, is the shape the
  VM sources set. A separate registry source that reads every image in a repository, running or
  not, answers a different question, "what could be deployed", and is deliberately not this.
- **Kubernetes.** GKE and EKS pods carry `status.containerStatuses[].imageID` with the pulled
  digest, which is the same design with a Kubernetes roster. Nodes are VMs. Not in scope here,
  and nothing above precludes it.
