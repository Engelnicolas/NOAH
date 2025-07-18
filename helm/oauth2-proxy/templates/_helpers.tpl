{{/*
Expand the name of the chart.
*/}}
{{- define "oauth2-proxy.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "oauth2-proxy.fullname" -}}
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
{{- define "oauth2-proxy.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "oauth2-proxy.labels" -}}
helm.sh/chart: {{ include "oauth2-proxy.chart" . }}
{{ include "oauth2-proxy.selectorLabels" . }}
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
{{- define "oauth2-proxy.selectorLabels" -}}
app.kubernetes.io/name: {{ include "oauth2-proxy.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "oauth2-proxy.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "oauth2-proxy.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use for OAuth2 credentials
*/}}
{{- define "oauth2-proxy.secretName" -}}
{{- if .Values.oauth2.existingSecret }}
{{- .Values.oauth2.existingSecret }}
{{- else }}
{{- include "oauth2-proxy.fullname" . }}-oauth2
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use for cookie secret
*/}}
{{- define "oauth2-proxy.cookieSecretName" -}}
{{- if .Values.oauth2.cookieSecretExistingSecret }}
{{- .Values.oauth2.cookieSecretExistingSecret }}
{{- else }}
{{- include "oauth2-proxy.fullname" . }}-cookie
{{- end }}
{{- end }}

{{/*
Get the Redis host
*/}}
{{- define "oauth2-proxy.redis.host" -}}
{{- if .Values.redis.enabled }}
{{- printf "%s-redis-master" .Release.Name }}
{{- else }}
{{- .Values.externalRedis.host }}
{{- end }}
{{- end }}

{{/*
Get the Redis password secret name
*/}}
{{- define "oauth2-proxy.redis.secretName" -}}
{{- if .Values.redis.enabled }}
{{- printf "%s-redis" .Release.Name }}
{{- else if .Values.externalRedis.existingSecret }}
{{- .Values.externalRedis.existingSecret }}
{{- else }}
{{- include "oauth2-proxy.fullname" . }}-redis
{{- end }}
{{- end }}

{{/*
Get the Redis password secret key
*/}}
{{- define "oauth2-proxy.redis.secretKey" -}}
{{- if .Values.redis.enabled }}
{{- "redis-password" }}
{{- else }}
{{- .Values.externalRedis.existingSecretPasswordKey | default "redis-password" }}
{{- end }}
{{- end }}

{{/*
Common annotations
*/}}
{{- define "oauth2-proxy.annotations" -}}
{{- with .Values.commonAnnotations }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Create image pull secrets
*/}}
{{- define "oauth2-proxy.imagePullSecrets" -}}
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
Get the image repository
*/}}
{{- define "oauth2-proxy.image.repository" -}}
{{- $registry := .Values.global.imageRegistry | default .Values.image.registry }}
{{- if $registry }}
{{- printf "%s/%s" $registry .Values.image.repository }}
{{- else }}
{{- .Values.image.repository }}
{{- end }}
{{- end }}

{{/*
Generate OAuth2 Proxy command line arguments
*/}}
{{- define "oauth2-proxy.args" -}}
- --provider={{ .Values.oauth2.provider }}
- --oidc-issuer-url={{ .Values.oauth2.oidcIssuerUrl }}
- --client-id={{ .Values.oauth2.clientId }}
- --email-domain={{ join "," .Values.oauth2.emailDomains }}
- --upstream={{ join "," .Values.oauth2.upstreams }}
- --http-address=0.0.0.0:4180
{{- if .Values.metrics.enabled }}
- --metrics-address=0.0.0.0:{{ .Values.metrics.port }}
{{- end }}
- --cookie-name={{ .Values.oauth2.cookieName }}
- --cookie-domain={{ .Values.oauth2.cookieDomain }}
- --cookie-expire={{ .Values.oauth2.cookieExpire }}
- --cookie-refresh={{ .Values.oauth2.cookieRefresh }}
- --cookie-secure={{ .Values.oauth2.cookieSecure }}
- --cookie-httponly={{ .Values.oauth2.cookieHttpOnly }}
- --cookie-samesite={{ .Values.oauth2.cookieSameSite }}
{{- if eq .Values.oauth2.sessionStorageType "redis" }}
- --session-store-type=redis
- --redis-connection-url=redis://{{ include "oauth2-proxy.redis.host" . }}:{{ .Values.redis.master.service.ports.redis | default .Values.externalRedis.port | default 6379 }}/{{ .Values.externalRedis.database | default 0 }}
{{- end }}
- --scope={{ .Values.oauth2.scope }}
{{- range .Values.oauth2.skipAuthRegex }}
- --skip-auth-regex={{ . }}
{{- end }}
{{- if .Values.oauth2.passAuthorizationHeader }}
- --pass-authorization-header={{ .Values.oauth2.passAuthorizationHeader }}
{{- end }}
{{- if .Values.oauth2.passAccessToken }}
- --pass-access-token={{ .Values.oauth2.passAccessToken }}
{{- end }}
{{- if .Values.oauth2.passUserHeaders }}
- --pass-user-headers={{ .Values.oauth2.passUserHeaders }}
{{- end }}
{{- if .Values.oauth2.setAuthorizationHeader }}
- --set-authorization-header={{ .Values.oauth2.setAuthorizationHeader }}
{{- end }}
{{- if .Values.oauth2.setXAuthRequestHeaders }}
- --set-xauthrequest={{ .Values.oauth2.setXAuthRequestHeaders }}
{{- end }}
{{- if .Values.oauth2.requestLogging }}
- --request-logging={{ .Values.oauth2.requestLogging }}
{{- end }}
{{- if .Values.oauth2.standardLogging }}
- --standard-logging={{ .Values.oauth2.standardLogging }}
{{- end }}
{{- if .Values.oauth2.authLogging }}
- --auth-logging={{ .Values.oauth2.authLogging }}
{{- end }}
{{- if .Values.oauth2.forceHttps }}
- --force-https={{ .Values.oauth2.forceHttps }}
{{- end }}
{{- if .Values.oauth2.insecureOidcAllowUnverifiedEmail }}
- --insecure-oidc-allow-unverified-email={{ .Values.oauth2.insecureOidcAllowUnverifiedEmail }}
{{- end }}
{{- if .Values.oauth2.insecureOidcSkipIssuerVerification }}
- --insecure-oidc-skip-issuer-verification={{ .Values.oauth2.insecureOidcSkipIssuerVerification }}
{{- end }}
{{- if .Values.oauth2.skipJwtBearerTokens }}
- --skip-jwt-bearer-tokens={{ .Values.oauth2.skipJwtBearerTokens }}
{{- end }}
- --flush-interval={{ .Values.oauth2.flushInterval }}
{{- range .Values.oauth2.extraArgs }}
- {{ . }}
{{- end }}
{{- end }}

{{/*
Redis fullname
*/}}
{{- define "oauth2-proxy.redis.fullname" -}}
{{- printf "%s-redis" (include "oauth2-proxy.fullname" .) }}
{{- end }}
