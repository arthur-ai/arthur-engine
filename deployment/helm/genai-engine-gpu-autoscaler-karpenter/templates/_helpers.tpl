{{/*
Expand the name of the chart.
*/}}
{{- define "gpu-autoscaler.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "gpu-autoscaler.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Chart name and version as used by the chart label.
*/}}
{{- define "gpu-autoscaler.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "gpu-autoscaler.labels" -}}
helm.sh/chart: {{ include "gpu-autoscaler.chart" . }}
app.kubernetes.io/name: {{ include "gpu-autoscaler.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Name of the genai-engine Deployment this HPA targets (honors an optional resourceNameSuffix).
*/}}
{{- define "gpu-autoscaler.targetDeploymentName" -}}
{{- $suffix := .Values.targetDeployment.resourceNameSuffix | default "" -}}
{{- if $suffix -}}
{{- printf "%s-%s" .Values.targetDeployment.name $suffix -}}
{{- else -}}
{{- .Values.targetDeployment.name -}}
{{- end -}}
{{- end }}
