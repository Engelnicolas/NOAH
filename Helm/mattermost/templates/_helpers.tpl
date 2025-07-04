{{/*
Expand the name of the chart.
*/}}
{{- define "mattermost.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "mattermost.fullname" -}}
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
{{- define "mattermost.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "mattermost.labels" -}}
helm.sh/chart: {{ include "mattermost.chart" . }}
{{ include "mattermost.selectorLabels" . }}
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
{{- define "mattermost.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mattermost.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "mattermost.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "mattermost.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use for OIDC credentials
*/}}
{{- define "mattermost.oidcSecretName" -}}
{{- if .Values.oidc.existingSecret }}
{{- .Values.oidc.existingSecret }}
{{- else }}
{{- include "mattermost.fullname" . }}-oidc
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use for LDAP credentials
*/}}
{{- define "mattermost.ldapSecretName" -}}
{{- if .Values.ldap.existingSecret }}
{{- .Values.ldap.existingSecret }}
{{- else }}
{{- include "mattermost.fullname" . }}-ldap
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use for database credentials
*/}}
{{- define "mattermost.databaseSecretName" -}}
{{- if .Values.database.existingSecret }}
{{- .Values.database.existingSecret }}
{{- else }}
{{- include "mattermost.fullname" . }}-database
{{- end }}
{{- end }}

{{/*
Get the database host
*/}}
{{- define "mattermost.database.host" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" .Release.Name }}
{{- else }}
{{- .Values.database.host }}
{{- end }}
{{- end }}

{{/*
Get the Redis host
*/}}
{{- define "mattermost.redis.host" -}}
{{- if .Values.redis.enabled }}
{{- printf "%s-redis-master" .Release.Name }}
{{- else }}
{{- .Values.redis.host }}
{{- end }}
{{- end }}

{{/*
Get the Elasticsearch host
*/}}
{{- define "mattermost.elasticsearch.host" -}}
{{- if .Values.elasticsearch.enabled }}
{{- printf "%s-elasticsearch" .Release.Name }}
{{- else }}
{{- .Values.elasticsearch.host }}
{{- end }}
{{- end }}

{{/*
Common annotations
*/}}
{{- define "mattermost.annotations" -}}
{{- with .Values.commonAnnotations }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Create image pull secrets
*/}}
{{- define "mattermost.imagePullSecrets" -}}
{{- if or .Values.image.pullSecrets .Values.global.imagePullSecrets }}
imagePullSecrets:
{{- range .Values.image.pullSecrets }}
  - name: {{ . }}
{{- end }}
{{- range .Values.global.imagePullSecrets }}
  - name: {{ . }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Get the image registry
*/}}
{{- define "mattermost.image.registry" -}}
{{- if .Values.global.imageRegistry }}
{{- .Values.global.imageRegistry }}
{{- else }}
{{- .Values.image.registry }}
{{- end }}
{{- end }}

{{/*
Get the image repository
*/}}
{{- define "mattermost.image.repository" -}}
{{- $registry := include "mattermost.image.registry" . }}
{{- if $registry }}
{{- printf "%s/%s" $registry .Values.image.repository }}
{{- else }}
{{- .Values.image.repository }}
{{- end }}
{{- end }}

{{/*
Get the storage class
*/}}
{{- define "mattermost.storageClass" -}}
{{- if .Values.global.storageClass }}
{{- .Values.global.storageClass }}
{{- else }}
{{- .Values.persistence.storageClass }}
{{- end }}
{{- end }}

{{/*
Generate database connection string
*/}}
{{- define "mattermost.database.connectionString" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "postgres://%s:%s@%s:%d/%s?sslmode=disable&connect_timeout=10" .Values.postgresql.auth.username .Values.postgresql.auth.password (include "mattermost.database.host" .) 5432 .Values.postgresql.auth.database }}
{{- else }}
{{- printf "postgres://%s:%s@%s:%d/%s?sslmode=disable&connect_timeout=10" .Values.database.user .Values.database.password .Values.database.host (int .Values.database.port) .Values.database.name }}
{{- end }}
{{- end }}
