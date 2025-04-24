{{/*
Chart name and version as used by the chart label.
*/}}
{{- define "arthur-ml-engine.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | lower | replace " " "-" | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "arthur-ml-engine.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name | lower | replace " " "-" }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "arthur-ml-engine.labels" -}}
helm.sh/chart: {{ include "arthur-ml-engine.chart" . }}
{{ include "arthur-ml-engine.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "arthur-ml-engine.serviceAccountName" -}}
{{- if .Values.mlEngineServiceAccount.create }}
{{- default (include "arthur-ml-engine.fullname" .) .Values.mlEngineServiceAccount.name }}
{{- else }}
{{- default "default" .Values.mlEngineServiceAccount.name }}
{{- end }}
{{- end }}
