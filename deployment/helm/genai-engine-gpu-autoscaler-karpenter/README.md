# Arthur GenAI Engine GPU Autoscaler

A standalone Helm add-on chart that autoscales the GenAI Engine's **GPU pods** on **GPU utilization** and **GPU memory usage**, for the Deployment/Karpenter path on **AWS EKS Auto Mode**. It leaves the core `genai-engine` chart untouched apart from one small opt-in flag.

## Design

```
 dcgm-exporter (DaemonSet, GPU nodes)  ──scrape──▶  Prometheus  ──▶  prometheus-adapter
   DCGM_FI_DEV_GPU_UTIL (%)                                          exposes custom.metrics.k8s.io:
   DCGM_FI_DEV_FB_USED / _FB_FREE (MiB)                               • DCGM_FI_DEV_GPU_UTIL   (per pod)
        │ (workload pod identity via kubernetes.enablePodLabels)      • gpu_mem_used_percent   (per pod, derived)
        ▼                                                                       │
 one engine pod per GPU node ⇒ per-node metric ≡ per-pod metric                 ▼
                                                          HPA (autoscaling/v2, type: Pods, AverageValue)
                                                                 │ scales replicas
                                                                 ▼
                                                   pending pods ⇒ Karpenter provisions g4dn nodes
```

- **HPA scales pods; Karpenter scales nodes.** When average GPU load crosses target, the HPA adds a replica → the new pod is unschedulable → Karpenter provisions a GPU node. When load falls, the HPA removes replicas → Karpenter consolidates idle nodes.
- **One engine pod per GPU node.** The engine's 7-CPU request keeps a single engine pod on each `g4dn.2xlarge`, so the per-node GPU metric equals the per-pod metric and a `type: Pods` / `AverageValue` HPA gives clean "average GPU load across replicas" semantics.
- **Replica-ownership handoff.** An external HPA cannot coexist with a Deployment that hard-pins `replicas`. The genai-engine chart exposes `arthurGenaiEngineHPA.externallyManaged: true`, which makes it drop the static `replicas` field and skip its own HPA, ceding scaling to this add-on.
- **Derived GPU memory metric.** `gpu_mem_used_percent = 100 * FB_USED / (FB_USED + FB_FREE)`, computed by a prometheus-adapter rule. With the ServiceMonitor's `honorLabels: false`, the workload pod surfaces as `exported_pod`/`exported_namespace`, which the rules map to the `pod`/`namespace` resources.

### What the chart installs

| Component | Source | Toggle |
| --- | --- | --- |
| HorizontalPodAutoscaler (GPU metrics) | this chart (`templates/hpa.yaml`) | always |
| NVIDIA DCGM exporter + its ServiceMonitor | `dcgm-exporter` subchart | `dcgm-exporter.enabled` |
| prometheus-adapter + GPU metric rules | `prometheus-adapter` subchart | `prometheus-adapter.enabled` |

## Prerequisites

- EKS Auto Mode cluster with a **GPU NodePool** (label `capability: gpu`, taint `nvidia.com/gpu=true:NoSchedule`) and an `nvidia.com/gpu` limit.
- **Prometheus Operator** running in-cluster (e.g. kube-prometheus-stack). This chart does **not** install Prometheus.
- The `genai-engine` chart at a version that supports `arthurGenaiEngineHPA.externallyManaged` (see compatibility below).
- Only **one** prometheus-adapter may serve `custom.metrics.k8s.io` per cluster — if you already run one, set `prometheus-adapter.enabled=false` and add the two rules from [values.yaml](values.yaml) to it instead.

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
     minReplicas: 2
     maxReplicas: 8                    # <= NodePool nvidia.com/gpu limit
     gpu:
       targetGPUUtilizationPercentage: 60
       targetGPUMemoryUtilizationPercentage: 80
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

4. **Hand replica ownership to the add-on** — set the gate on the genai-engine release and upgrade:
   ```yaml
   # genai-engine values
   arthurGenaiEngineHPA:
     enabled: false
     externallyManaged: true
   ```
   ```bash
   helm upgrade <genai-release> <genai-chart> -n <genai-engine-namespace> -f <genai-values>
   ```

5. **Verify metrics reach the HPA** (values, not errors / not `<unknown>`):
   ```bash
   kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1/namespaces/<ns>/pods/*/DCGM_FI_DEV_GPU_UTIL"
   kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1/namespaces/<ns>/pods/*/gpu_mem_used_percent"
   kubectl get hpa genai-gpu-autoscaler-genai-engine-gpu-autoscaler-karpenter -n <ns>
   ```

6. **Observe scaling under load:**
   ```bash
   kubectl get hpa,pods -n <ns> -w
   kubectl get nodes -l capability=gpu          # Karpenter provisioning/consolidating GPU nodes
   ```

7. **Uninstall / rollback:** `helm uninstall genai-gpu-autoscaler -n <ns>`, then revert `externallyManaged` to `false` (and re-enable the in-chart HPA if desired) on the genai-engine release.

## Bring your own metric pipeline

- Already run DCGM exporter? `--set dcgm-exporter.enabled=false` (ensure its metrics carry the workload pod identity and are scraped by Prometheus).
- Already run prometheus-adapter? `--set prometheus-adapter.enabled=false` and copy the two `rules.custom` entries from [values.yaml](values.yaml) into it.

## Compatibility

| This add-on | Requires genai-engine chart |
| --- | --- |
| 0.1.0 | version with `arthurGenaiEngineHPA.externallyManaged` support (>= the release that introduces it) |
