{{/*
Expand the name of the chart.
*/}}
{{- define "arthur-genai-engine.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "arthur-genai-engine.fullname" -}}
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
Create chart name and version as used by the chart label.
*/}}
{{- define "arthur-genai-engine.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "arthur-genai-engine.labels" -}}
helm.sh/chart: {{ include "arthur-genai-engine.chart" . }}
{{ include "arthur-genai-engine.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "arthur-genai-engine.selectorLabels" -}}
app.kubernetes.io/name: {{ include "arthur-genai-engine.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "arthur-genai-engine.serviceAccountName" -}}
{{- if .Values.genaiEngineServiceAccount.create }}
{{- default (include "arthur-genai-engine.fullname" .) .Values.genaiEngineServiceAccount.name }}
{{- else }}
{{- default "default" .Values.genaiEngineServiceAccount.name }}
{{- end }}
{{- end }}

{{/*
GCP credentials for the Vertex AI model provider's default credentials. gcpCredentials
replaces gcpDiscoveryConfig, which is still read: whichever block is enabled is used, and
gcpCredentials wins when both are. A disabled new block does not hide an enabled old one.
*/}}
{{- define "arthur-genai-engine.gcpCredentials" -}}
{{- $new := .Values.gcpCredentials | default dict -}}
{{- $old := .Values.gcpDiscoveryConfig | default dict -}}
{{- if $new.isEnabled -}}
{{- toYaml $new -}}
{{- else if $old.isEnabled -}}
{{- toYaml $old -}}
{{- else -}}
{{- toYaml dict -}}
{{- end -}}
{{- end }}
