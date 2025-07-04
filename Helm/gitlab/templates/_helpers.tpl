{{/*
Expand the name of the chart.
*/}}
{{- define "gitlab.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "gitlab.fullname" -}}
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
{{- define "gitlab.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "gitlab.labels" -}}
helm.sh/chart: {{ include "gitlab.chart" . }}
{{ include "gitlab.selectorLabels" . }}
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
{{- define "gitlab.selectorLabels" -}}
app.kubernetes.io/name: {{ include "gitlab.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
GitLab Runner labels
*/}}
{{- define "gitlab.runner.labels" -}}
helm.sh/chart: {{ include "gitlab.chart" . }}
{{ include "gitlab.runner.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
GitLab Runner selector labels
*/}}
{{- define "gitlab.runner.selectorLabels" -}}
app.kubernetes.io/name: gitlab-runner
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "gitlab.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "gitlab.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Return the GitLab secret name
*/}}
{{- define "gitlab.secretName" -}}
{{- if .Values.gitlab.existingSecret }}
{{- printf "%s" .Values.gitlab.existingSecret }}
{{- else }}
{{- printf "%s" (include "gitlab.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Return the PostgreSQL hostname
*/}}
{{- define "gitlab.postgresql.host" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" (include "gitlab.fullname" .) }}
{{- else }}
{{- printf "%s" .Values.database.hostname }}
{{- end }}
{{- end }}

{{/*
Return the Redis hostname
*/}}
{{- define "gitlab.redis.host" -}}
{{- if .Values.redis.enabled }}
{{- printf "%s-redis-master" (include "gitlab.fullname" .) }}
{{- else }}
{{- printf "%s" .Values.externalRedis.host }}
{{- end }}
{{- end }}

{{/*
Return the OIDC secret name
*/}}
{{- define "gitlab.oidcSecretName" -}}
{{- if .Values.oidc.existingSecret }}
{{- printf "%s" .Values.oidc.existingSecret }}
{{- else }}
{{- printf "%s-oidc" (include "gitlab.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Return the LDAP secret name
*/}}
{{- define "gitlab.ldapSecretName" -}}
{{- if .Values.ldap.existingSecret }}
{{- printf "%s" .Values.ldap.existingSecret }}
{{- else }}
{{- printf "%s-ldap" (include "gitlab.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Return the GitLab Runner secret name
*/}}
{{- define "gitlab.runner.secretName" -}}
{{- printf "%s-runner" (include "gitlab.fullname" .) }}
{{- end }}

{{/*
Return the ingress TLS secret name
*/}}
{{- define "gitlab.tlsSecretName" -}}
{{- if .Values.ingress.tls.secretName }}
{{- printf "%s" .Values.ingress.tls.secretName }}
{{- else }}
{{- printf "%s-tls" (include "gitlab.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Return true if a secret should be created for GitLab
*/}}
{{- define "gitlab.createSecret" -}}
{{- if or (not .Values.gitlab.existingSecret) (and .Values.oidc.enabled (not .Values.oidc.existingSecret)) (and .Values.ldap.enabled (not .Values.ldap.existingSecret)) }}
{{- true }}
{{- end }}
{{- end }}
