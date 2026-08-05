# Arthur GenAI Engine GPU Autoscaler

A standalone Helm add-on chart that autoscales the GenAI Engine's **GPU pods** on **GPU utilization**, for the Deployment/Karpenter path on **AWS EKS Auto Mode**. It leaves the core `genai-engine` chart untouched apart from two small opt-in values.

## Design

```
 dcgm-exporter (DaemonSet, GPU nodes)  ──scrape──▶  Prometheus  ──▶  prometheus-adapter
   DCGM_FI_DEV_GPU_UTIL (%)                                          exposes custom.metrics.k8s.io:
        │                                                             • DCGM_FI_DEV_GPU_UTIL   (per pod)
        │ (pod identity via the kubelet pod-resources API)                      │
        ▼                                                                       ▼
 one engine pod per GPU node ⇒ per-node metric ≡ per-pod metric                 │
                                                          HPA (autoscaling/v2, type: Pods, AverageValue)
                                                                 │ scales replicas
                                                                 ▼
                                                   pending pods ⇒ Karpenter provisions g4dn nodes
```

- **HPA scales pods; Karpenter scales nodes.** When average GPU load crosses target, the HPA adds a replica → the new pod is unschedulable → Karpenter provisions a GPU node. When load falls, the HPA removes replicas → Karpenter consolidates idle nodes.
- **One engine pod per GPU node.** The engine's 7-CPU request keeps a single engine pod on each `g4dn.2xlarge`, so the per-node GPU metric equals the per-pod metric and a `type: Pods` / `AverageValue` HPA gives clean "average GPU load across replicas" semantics.
- **Replica-ownership handoff.** An external HPA cannot coexist with a Deployment that hard-pins `replicas`. The genai-engine chart exposes `arthurGenaiEngineHPA.externallyManaged: true`, which makes it drop the static `replicas` field and skip its own HPA, ceding scaling to this add-on.
- **Pod identity on the metrics.** With the ServiceMonitor's `honorLabels: false`, the workload pod surfaces as `exported_pod`/`exported_namespace`, which the adapter rule maps to the `pod`/`namespace` resources. DCGM only learns which pod owns a GPU from the kubelet pod-resources API, and that reports an allocation only for pods that *request* the device — hence the `genaiEngineContainerGPULimit` prerequisite below.
- **GPU utilization is the only scaling signal, deliberately.** GPU *memory* is not a load signal for this workload: the engine holds its model suite resident, so memory is roughly constant with respect to request volume, and adding a replica does not reduce any existing pod's GPU memory — each replica loads the same models onto its own GPU. An HPA metric on it could only ratchet upward, pinning at `maxReplicas` whenever idle memory exceeded the target, with no path back down. DCGM's raw `DCGM_FI_DEV_FB_USED` / `_FB_FREE` remain in Prometheus for dashboards and capacity planning.

### What the chart installs

| Component | Source | Toggle |
| --- | --- | --- |
| HorizontalPodAutoscaler (GPU utilization) | this chart (`templates/hpa.yaml`) | always |
| NVIDIA DCGM exporter + its ServiceMonitor | `dcgm-exporter` subchart | `dcgm-exporter.enabled` |
| prometheus-adapter + GPU metric rule | `prometheus-adapter` subchart | `prometheus-adapter.enabled` |

## Prerequisites

- EKS Auto Mode cluster with a **GPU NodePool** (label `capability: gpu`, taint `nvidia.com/gpu=true:NoSchedule`) and an `nvidia.com/gpu` limit.
- **A device plugin advertising `nvidia.com/gpu`**, and `genaiEngineContainerGPULimit: "1"` set on the genai-engine release. Without a device *request* on the engine pod, the kubelet pod-resources API reports no allocation, DCGM cannot attribute GPU metrics to a pod, and the HPA reads `<unknown>` forever. Confirm the resource exists first, or the pod will never schedule:
  ```bash
  kubectl get node <gpu-node> -o jsonpath='{.status.allocatable}' | tr ',' '\n' | grep nvidia
  ```
- **Prometheus Operator** running in-cluster (e.g. kube-prometheus-stack). This chart does **not** install Prometheus.
- The `genai-engine` chart at a version that supports `arthurGenaiEngineHPA.externallyManaged` and `genaiEngineContainerGPULimit` (see compatibility below).
- Only **one** prometheus-adapter may serve `custom.metrics.k8s.io` per cluster — if you already run one, set `prometheus-adapter.enabled=false` and add the rule from [values.yaml](values.yaml) to it instead.

## Step-by-step usage

1. **Write an overrides file.** The chart's documented defaults live in [values.yaml](values.yaml); you only need to override what differs in your cluster. In a `my-values.yaml`:
   ```yaml
   targetDeployment:
     name: arthur-genai-engine        # + resourceNameSuffix if your release uses one
   prometheus-adapter:
     prometheus:
       url: http://prometheus-operated.monitoring.svc   # your in-cluster Prometheus
   dcgm-exporter:
     serviceMonitor:
       additionalLabels:
         release: kube-prometheus-stack   # label your Prometheus selects ServiceMonitors by
   hpa:
     minReplicas: 2                    # raise from the default of 1 to stay multi-replica when idle
     maxReplicas: 4                    # <= NodePool nvidia.com/gpu limit; each replica costs a GPU node
     gpu:
       targetGPUUtilizationPercentage: 60
   ```

2. **Fetch the subcharts:**
   ```bash
   helm dependency update deployment/helm/genai-engine-gpu-autoscaler-karpenter
   ```

3. **Install into the genai-engine namespace** (the HPA must live where the Deployment lives):
   ```bash
   helm install genai-gpu-autoscaler \
     deployment/helm/genai-engine-gpu-autoscaler-karpenter \
     -n <genai-engine-namespace> -f my-values.yaml
   ```

4. **Hand replica ownership to the add-on, and request the GPU** — set both on the genai-engine release and upgrade:
   ```yaml
   # genai-engine values
   arthurGenaiEngineHPA:
     enabled: false
     externallyManaged: true
   genaiEngineContainerGPULimit: "1"    # required for per-pod GPU metrics; see Prerequisites
   ```
   ```bash
   helm upgrade <genai-release> <genai-chart> -n <genai-engine-namespace> -f <genai-values>
   ```

5. **Verify the metric reaches the HPA** (values, not errors / not `<unknown>`):
   ```bash
   kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1/namespaces/<ns>/pods/*/DCGM_FI_DEV_GPU_UTIL"
   kubectl get hpa genai-gpu-autoscaler-genai-engine-gpu-autoscaler-karpenter -n <ns>
   ```
   An empty `items` list almost always means the metrics carry no pod identity — check that `genaiEngineContainerGPULimit` is set and that the exporter's output has a pod label:
   ```bash
   kubectl port-forward -n <ns> ds/genai-gpu-autoscaler-dcgm-exporter 9400:9400 &
   curl -s localhost:9400/metrics | grep DCGM_FI_DEV_GPU_UTIL
   ```
   (The exporter image is distroless — `kubectl exec ... curl` will not work.)

6. **Observe scaling under load:**
   ```bash
   kubectl get hpa,pods -n <ns> -w
   kubectl get nodes -l capability=gpu          # Karpenter provisioning/consolidating GPU nodes
   ```

7. **Uninstall / rollback:** `helm uninstall genai-gpu-autoscaler -n <ns>`, then revert `externallyManaged` to `false` (and re-enable the in-chart HPA if desired) on the genai-engine release.

## Bring your own metric pipeline

- Already run DCGM exporter? `--set dcgm-exporter.enabled=false` (ensure its metrics carry the workload pod identity and are scraped by Prometheus).
- Already run prometheus-adapter? `--set prometheus-adapter.enabled=false` and copy the `rules.custom` entry from [values.yaml](values.yaml) into it.

## Compatibility

| This add-on | Requires genai-engine chart |
| --- | --- |
| 0.1.0 | version with `arthurGenaiEngineHPA.externallyManaged` and `genaiEngineContainerGPULimit` support (>= the release that introduces them) |
