{{/*
Expand the name of the chart.
*/}}
{{- define "prometheus.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "prometheus.fullname" -}}
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
{{- define "prometheus.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "prometheus.labels" -}}
helm.sh/chart: {{ include "prometheus.chart" . }}
{{ include "prometheus.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "prometheus.selectorLabels" -}}
app.kubernetes.io/name: {{ include "prometheus.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Grafana labels
*/}}
{{- define "grafana.labels" -}}
helm.sh/chart: {{ include "prometheus.chart" . }}
{{ include "grafana.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Grafana selector labels
*/}}
{{- define "grafana.selectorLabels" -}}
app.kubernetes.io/name: grafana
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
AlertManager labels
*/}}
{{- define "alertmanager.labels" -}}
helm.sh/chart: {{ include "prometheus.chart" . }}
{{ include "alertmanager.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
AlertManager selector labels
*/}}
{{- define "alertmanager.selectorLabels" -}}
app.kubernetes.io/name: alertmanager
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Node Exporter labels
*/}}
{{- define "nodeexporter.labels" -}}
helm.sh/chart: {{ include "prometheus.chart" . }}
{{ include "nodeexporter.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Node Exporter selector labels
*/}}
{{- define "nodeexporter.selectorLabels" -}}
app.kubernetes.io/name: node-exporter
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "prometheus.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "prometheus.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Prometheus fullname
*/}}
{{- define "prometheus.prometheus.fullname" -}}
{{- printf "%s-prometheus" (include "prometheus.fullname" .) }}
{{- end }}

{{/*
Grafana fullname
*/}}
{{- define "prometheus.grafana.fullname" -}}
{{- printf "%s-grafana" (include "prometheus.fullname" .) }}
{{- end }}

{{/*
AlertManager fullname
*/}}
{{- define "prometheus.alertmanager.fullname" -}}
{{- printf "%s-alertmanager" (include "prometheus.fullname" .) }}
{{- end }}

{{/*
Node Exporter fullname
*/}}
{{- define "prometheus.nodeexporter.fullname" -}}
{{- printf "%s-node-exporter" (include "prometheus.fullname" .) }}
{{- end }}

{{/*
Return the Prometheus secret name
*/}}
{{- define "prometheus.secretName" -}}
{{- if .Values.prometheus.existingSecret }}
{{- printf "%s" .Values.prometheus.existingSecret }}
{{- else }}
{{- printf "%s" (include "prometheus.prometheus.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Return the Grafana secret name
*/}}
{{- define "grafana.secretName" -}}
{{- if .Values.grafana.auth.existingSecret }}
{{- printf "%s" .Values.grafana.auth.existingSecret }}
{{- else }}
{{- printf "%s" (include "prometheus.grafana.fullname" .) }}
{{- end }}
{{- end }}
