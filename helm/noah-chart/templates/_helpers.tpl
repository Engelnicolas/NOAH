{{/*
Expand the name of the chart.
*/}}
{{- define "noah-chart.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "noah-chart.fullname" -}}
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
{{- define "noah-chart.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "noah-chart.labels" -}}
helm.sh/chart: {{ include "noah-chart.chart" . }}
{{ include "noah-chart.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- if .Values.global.labels }}
{{ toYaml .Values.global.labels }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "noah-chart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "noah-chart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "noah-chart.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "noah-chart.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Common security context
*/}}
{{- define "noah-chart.securityContext" -}}
{{- if .Values.global.securityContext }}
{{- toYaml .Values.global.securityContext }}
{{- else }}
runAsNonRoot: true
runAsUser: 1000
fsGroup: 1000
{{- end }}
{{- end }}

{{/*
Common resource limits
*/}}
{{- define "noah-chart.resources" -}}
{{- if .resources }}
{{- toYaml .resources }}
{{- else }}
requests:
  memory: "256Mi"
  cpu: "250m"
limits:
  memory: "512Mi"
  cpu: "500m"
{{- end }}
{{- end }}

{{/*
Generate certificates secret name
*/}}
{{- define "noah-chart.tlsSecretName" -}}
{{- printf "%s-tls" (include "noah-chart.fullname" .) }}
{{- end }}

{{/*
Common ingress annotations
*/}}
{{- define "noah-chart.ingressAnnotations" -}}
kubernetes.io/ingress.class: "nginx"
cert-manager.io/cluster-issuer: "letsencrypt-prod"
nginx.ingress.kubernetes.io/ssl-redirect: "true"
nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
{{- end }}
