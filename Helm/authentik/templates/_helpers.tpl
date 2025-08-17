{{/*
Expand the name of the chart.
*/}}
{{- define "authentik.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "authentik.fullname" -}}
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
{{- define "authentik.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "authentik.labels" -}}
helm.sh/chart: {{ include "authentik.chart" . }}
{{ include "authentik.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "authentik.selectorLabels" -}}
app.kubernetes.io/name: {{ include "authentik.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
PostgreSQL host
*/}}
{{- define "authentik.postgresql.host" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" (include "authentik.fullname" .) }}
{{- else }}
{{- .Values.externalDatabase.host }}
{{- end }}
{{- end }}

{{/*
Redis host
*/}}
{{- define "authentik.redis.host" -}}
{{- if .Values.redis.enabled }}
{{- printf "%s-redis-master" (include "authentik.fullname" .) }}
{{- else }}
{{- .Values.externalRedis.host }}
{{- end }}
{{- end }}
