{{/*
Expand the name of the chart.
*/}}
{{- define "noah.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "noah.fullname" -}}
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
{{- define "noah.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels for all NOAH components
*/}}
{{- define "noah.labels" -}}
helm.sh/chart: {{ include "noah.chart" . }}
{{ include "noah.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: noah
{{- end }}

{{/*
Selector labels
*/}}
{{- define "noah.selectorLabels" -}}
app.kubernetes.io/name: {{ include "noah.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Pod Security Context - Default secure settings
*/}}
{{- define "noah.podSecurityContext" -}}
runAsNonRoot: true
runAsUser: {{ .Values.securityContext.runAsUser | default 1000 }}
runAsGroup: {{ .Values.securityContext.runAsGroup | default 1000 }}
fsGroup: {{ .Values.securityContext.fsGroup | default 1000 }}
seccompProfile:
  type: RuntimeDefault
{{- end }}

{{/*
Container Security Context - Default secure settings
*/}}
{{- define "noah.securityContext" -}}
runAsNonRoot: true
runAsUser: {{ .Values.securityContext.runAsUser | default 1000 }}
runAsGroup: {{ .Values.securityContext.runAsGroup | default 1000 }}
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
{{- if .Values.securityContext.readOnlyRootFilesystem }}
readOnlyRootFilesystem: true
{{- end }}
{{- end }}

{{/*
Create a default storage class name
*/}}
{{- define "noah.storageClass" -}}
{{- if .Values.global.storageClass -}}
{{- .Values.global.storageClass -}}
{{- else if .Values.persistence.storageClass -}}
{{- .Values.persistence.storageClass -}}
{{- else -}}
{{- "" -}}
{{- end -}}
{{- end }}
