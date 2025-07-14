{{/*
====================================
NOAH Common Library Template Helpers
====================================
Shared template functions for all NOAH Helm charts
*/}}

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
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "noah.selectorLabels" -}}
app.kubernetes.io/name: {{ include "noah.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "noah.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "noah.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Return the appropriate apiVersion for HPA
*/}}
{{- define "noah.hpa.apiVersion" -}}
{{- if semverCompare ">=1.23-0" .Capabilities.KubeVersion.GitVersion -}}
{{- print "autoscaling/v2" -}}
{{- else if semverCompare ">=1.12-0" .Capabilities.KubeVersion.GitVersion -}}
{{- print "autoscaling/v2beta2" -}}
{{- else -}}
{{- print "autoscaling/v2beta1" -}}
{{- end -}}
{{- end -}}

{{/*
Return the appropriate apiVersion for NetworkPolicy
*/}}
{{- define "noah.networkPolicy.apiVersion" -}}
{{- if semverCompare ">=1.25-0" .Capabilities.KubeVersion.GitVersion -}}
{{- print "networking.k8s.io/v1" -}}
{{- else -}}
{{- print "networking.k8s.io/v1beta1" -}}
{{- end -}}
{{- end -}}

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
{{- end -}}

{{/*
Database connection string helper
*/}}
{{- define "noah.database.connectionString" -}}
{{- if .Values.postgresql.enabled -}}
postgresql://{{ .Values.postgresql.auth.username }}:{{ .Values.postgresql.auth.password }}@{{ include "noah.fullname" . }}-postgresql:5432/{{ .Values.postgresql.auth.database }}
{{- else if .Values.externalDatabase.host -}}
postgresql://{{ .Values.externalDatabase.username }}:{{ .Values.externalDatabase.password }}@{{ .Values.externalDatabase.host }}:{{ .Values.externalDatabase.port }}/{{ .Values.externalDatabase.database }}
{{- end -}}
{{- end -}}

{{/*
Redis connection string helper
*/}}
{{- define "noah.redis.connectionString" -}}
{{- if .Values.redis.enabled -}}
redis://{{ include "noah.fullname" . }}-redis:6379
{{- else if .Values.externalRedis.host -}}
redis://{{ .Values.externalRedis.host }}:{{ .Values.externalRedis.port }}
{{- end -}}
{{- end -}}

{{/*
LDAP server URL helper
*/}}
{{- define "noah.ldap.url" -}}
{{- if .Values.samba4.enabled -}}
ldap://{{ .Release.Name }}-samba4:389
{{- else if .Values.externalLdap.host -}}
ldap://{{ .Values.externalLdap.host }}:{{ .Values.externalLdap.port }}
{{- end -}}
{{- end -}}

{{/*
Keycloak OIDC URL helper
*/}}
{{- define "noah.keycloak.url" -}}
{{- if .Values.keycloak.enabled -}}
http://{{ .Release.Name }}-keycloak:8080
{{- else if .Values.externalKeycloak.host -}}
{{ .Values.externalKeycloak.protocol }}://{{ .Values.externalKeycloak.host }}{{ if .Values.externalKeycloak.port }}:{{ .Values.externalKeycloak.port }}{{ end }}
{{- end -}}
{{- end -}}

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
