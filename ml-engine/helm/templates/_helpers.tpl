{{/*
Chart name and version as used by the chart label.
*/}}
{{- define "ml-engine.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | lower | replace " " "-" | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ml-engine.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name | lower | replace " " "-" }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "ml-engine.labels" -}}
helm.sh/chart: {{ include "ml-engine.chart" . }}
{{ include "ml-engine.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}
