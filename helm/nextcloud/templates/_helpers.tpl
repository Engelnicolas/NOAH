{{/*
Expand the name of the chart.
*/}}
{{- define "nextcloud.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "nextcloud.fullname" -}}
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
{{- define "nextcloud.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "nextcloud.labels" -}}
helm.sh/chart: {{ include "nextcloud.chart" . }}
{{ include "nextcloud.selectorLabels" . }}
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
{{- define "nextcloud.selectorLabels" -}}
app.kubernetes.io/name: {{ include "nextcloud.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "nextcloud.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "nextcloud.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use for admin credentials
*/}}
{{- define "nextcloud.secretName" -}}
{{- if .Values.nextcloud.existingSecret }}
{{- .Values.nextcloud.existingSecret }}
{{- else }}
{{- include "nextcloud.fullname" . }}-admin
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use for OIDC credentials
*/}}
{{- define "nextcloud.oidcSecretName" -}}
{{- if .Values.oidc.existingSecret }}
{{- .Values.oidc.existingSecret }}
{{- else }}
{{- include "nextcloud.fullname" . }}-oidc
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use for LDAP credentials
*/}}
{{- define "nextcloud.ldapSecretName" -}}
{{- if .Values.ldap.existingSecret }}
{{- .Values.ldap.existingSecret }}
{{- else }}
{{- include "nextcloud.fullname" . }}-ldap
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use for database credentials
*/}}
{{- define "nextcloud.databaseSecretName" -}}
{{- if .Values.database.existingSecret }}
{{- .Values.database.existingSecret }}
{{- else }}
{{- include "nextcloud.fullname" . }}-database
{{- end }}
{{- end }}

{{/*
Get the database host
*/}}
{{- define "nextcloud.database.host" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" .Release.Name }}
{{- else }}
{{- .Values.database.host }}
{{- end }}
{{- end }}

{{/*
Get the Redis host
*/}}
{{- define "nextcloud.redis.host" -}}
{{- if .Values.redis.enabled }}
{{- printf "%s-redis-master" .Release.Name }}
{{- else }}
{{- .Values.redis.host }}
{{- end }}
{{- end }}

{{/*
Get the admin username
*/}}
{{- define "nextcloud.admin.username" -}}
{{- if .Values.nextcloud.existingSecret }}
{{- .Values.nextcloud.existingSecretUsernameKey }}
{{- else }}
{{- .Values.nextcloud.adminUser }}
{{- end }}
{{- end }}

{{/*
Common annotations
*/}}
{{- define "nextcloud.annotations" -}}
{{- with .Values.commonAnnotations }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Create image pull secrets
*/}}
{{- define "nextcloud.imagePullSecrets" -}}
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
{{- define "nextcloud.image.registry" -}}
{{- if .Values.global.imageRegistry }}
{{- .Values.global.imageRegistry }}
{{- else }}
{{- .Values.image.registry }}
{{- end }}
{{- end }}

{{/*
Get the image repository
*/}}
{{- define "nextcloud.image.repository" -}}
{{- $registry := include "nextcloud.image.registry" . }}
{{- if $registry }}
{{- printf "%s/%s" $registry .Values.image.repository }}
{{- else }}
{{- .Values.image.repository }}
{{- end }}
{{- end }}

{{/*
Get the storage class
*/}}
{{- define "nextcloud.storageClass" -}}
{{- if .Values.global.storageClass }}
{{- .Values.global.storageClass }}
{{- else }}
{{- .Values.persistence.storageClass }}
{{- end }}
{{- end }}

{{/*
Generate environment variables for Nextcloud
*/}}
{{- define "nextcloud.environment" -}}
- name: NEXTCLOUD_ADMIN_USER
  valueFrom:
    secretKeyRef:
      name: {{ include "nextcloud.secretName" . }}
      key: {{ .Values.nextcloud.existingSecretUsernameKey | default "admin-username" }}
- name: NEXTCLOUD_ADMIN_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "nextcloud.secretName" . }}
      key: {{ .Values.nextcloud.existingSecretPasswordKey | default "admin-password" }}
- name: NEXTCLOUD_TRUSTED_DOMAINS
  value: {{ join " " .Values.nextcloud.trustedDomains | quote }}
- name: NEXTCLOUD_DATA_DIR
  value: {{ .Values.nextcloud.dataDir | quote }}
{{- if .Values.postgresql.enabled }}
- name: POSTGRES_HOST
  value: {{ include "nextcloud.database.host" . }}
- name: POSTGRES_DB
  value: {{ .Values.postgresql.auth.database | quote }}
- name: POSTGRES_USER
  value: {{ .Values.postgresql.auth.username | quote }}
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ .Release.Name }}-postgresql
      key: password
{{- else }}
- name: POSTGRES_HOST
  value: {{ .Values.database.host | quote }}
- name: POSTGRES_DB
  value: {{ .Values.database.name | quote }}
- name: POSTGRES_USER
  value: {{ .Values.database.user | quote }}
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "nextcloud.databaseSecretName" . }}
      key: {{ .Values.database.existingSecretPasswordKey | default "password" }}
{{- end }}
{{- if .Values.redis.enabled }}
- name: REDIS_HOST
  value: {{ include "nextcloud.redis.host" . }}
{{- if .Values.redis.auth.enabled }}
- name: REDIS_HOST_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ .Release.Name }}-redis
      key: redis-password
{{- end }}
{{- end }}
{{- if .Values.extraEnvVars }}
{{ toYaml .Values.extraEnvVars }}
{{- end }}
{{- end }}
