{{/*
Expand the name of the chart.
*/}}
{{- define "keycloak.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "keycloak.fullname" -}}
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
{{- define "keycloak.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "keycloak.labels" -}}
helm.sh/chart: {{ include "keycloak.chart" . }}
{{ include "keycloak.selectorLabels" . }}
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
{{- define "keycloak.selectorLabels" -}}
app.kubernetes.io/name: {{ include "keycloak.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "keycloak.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "keycloak.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Return the Keycloak secret name
*/}}
{{- define "keycloak.secretName" -}}
{{- if .Values.auth.existingSecret }}
{{- printf "%s" .Values.auth.existingSecret }}
{{- else }}
{{- printf "%s" (include "keycloak.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Return the PostgreSQL secret name
*/}}
{{- define "keycloak.postgresql.secretName" -}}
{{- if .Values.postgresql.auth.existingSecret }}
{{- printf "%s" .Values.postgresql.auth.existingSecret }}
{{- else }}
{{- printf "%s-postgresql" (include "keycloak.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Return the database hostname
*/}}
{{- define "keycloak.databaseHost" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" (include "keycloak.fullname" .) }}
{{- else }}
{{- printf "%s" .Values.database.hostname }}
{{- end }}
{{- end }}

{{/*
Return the LDAP secret name
*/}}
{{- define "keycloak.ldapSecretName" -}}
{{- if .Values.ldap.existingSecret }}
{{- printf "%s" .Values.ldap.existingSecret }}
{{- else }}
{{- printf "%s-ldap" (include "keycloak.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Return the ingress TLS secret name
*/}}
{{- define "keycloak.tlsSecretName" -}}
{{- if .Values.ingress.tls.secretName }}
{{- printf "%s" .Values.ingress.tls.secretName }}
{{- else }}
{{- printf "%s-tls" (include "keycloak.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Return true if a secret should be created for Keycloak
*/}}
{{- define "keycloak.createSecret" -}}
{{- if or (not .Values.auth.existingSecret) (and .Values.ldap.enabled (not .Values.ldap.existingSecret)) }}
{{- true }}
{{- end }}
{{- end }}

{{/*
Return the database URL
*/}}
{{- define "keycloak.databaseUrl" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "jdbc:postgresql://%s:%d/%s" (include "keycloak.databaseHost" .) (int .Values.database.port) .Values.database.database }}
{{- else }}
{{- printf "jdbc:postgresql://%s:%d/%s" .Values.database.hostname (int .Values.database.port) .Values.database.database }}
{{- end }}
{{- end }}
