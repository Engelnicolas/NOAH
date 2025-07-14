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
{{- if ne (.Values.securityContext.runAsUser | int) 0 }}
runAsNonRoot: true
{{- else }}
runAsNonRoot: false
{{- end }}
runAsUser: {{ .Values.securityContext.runAsUser | default 0 }}
runAsGroup: {{ .Values.securityContext.runAsGroup | default 0 }}
fsGroup: {{ .Values.securityContext.fsGroup | default 0 }}
seccompProfile:
  type: RuntimeDefault
{{- end }}

{{/*
Container Security Context - Default secure settings
*/}}
{{- define "noah.securityContext" -}}
{{- if ne (.Values.securityContext.runAsUser | int) 0 }}
runAsNonRoot: true
{{- else }}
runAsNonRoot: false
{{- end }}
runAsUser: {{ .Values.securityContext.runAsUser | default 0 }}
runAsGroup: {{ .Values.securityContext.runAsGroup | default 0 }}
allowPrivilegeEscalation: {{ .Values.securityContext.allowPrivilegeEscalation | default true }}
capabilities:
  {{- if eq (.Values.securityContext.runAsUser | int) 0 }}
  add:
    - CHOWN
    - DAC_OVERRIDE
    - FOWNER
    - SETGID
    - SETUID
  {{- else }}
  drop:
    - ALL
  {{- end }}
{{- if .Values.securityContext.readOnlyRootFilesystem }}
readOnlyRootFilesystem: true
{{- end }}
{{- end }}

{{/*
ServiceMonitor template
*/}}
{{- define "noah.serviceMonitor" -}}
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ include "noah.fullname" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "noah.labels" . | nindent 4 }}
spec:
  selector:
    matchLabels:
      {{- include "noah.selectorLabels" . | nindent 6 }}
  endpoints:
  - port: {{ .Values.serviceMonitor.port | default "http" }}
    path: {{ .Values.serviceMonitor.path | default "/metrics" }}
    interval: 30s
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
