{{/*
OAuth2 Proxy common labels
*/}}
{{- define "noah-common.oauth2.labels" -}}
app.kubernetes.io/name: oauth2-proxy
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: oauth2-proxy
app.kubernetes.io/part-of: noah
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
OAuth2 Proxy selector labels
*/}}
{{- define "noah-common.oauth2.selectorLabels" -}}
app.kubernetes.io/name: oauth2-proxy
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
OAuth2 Proxy deployment template
*/}}
{{- define "noah-common.oauth2.deployment" -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "noah-common.fullname" . }}-oauth2-proxy
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "noah-common.oauth2.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.oauth2proxy.replicaCount | default 1 }}
  selector:
    matchLabels:
      {{- include "noah-common.oauth2.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "noah-common.oauth2.selectorLabels" . | nindent 8 }}
    spec:
      containers:
      - name: oauth2-proxy
        image: "{{ .Values.oauth2proxy.image.repository }}:{{ .Values.oauth2proxy.image.tag }}"
        args:
        - --provider={{ .Values.oauth2proxy.provider }}
        - --oidc-issuer-url={{ printf "http://%s-keycloak.%s.svc.cluster.local:8080/realms/noah" (include "noah-common.fullname" .) .Release.Namespace }}
        - --client-id={{ .Values.oauth2proxy.clientId }}
        - --email-domain={{ .Values.oauth2proxy.emailDomain }}
        - --upstream={{ .Values.oauth2proxy.upstream }}
        - --http-address=0.0.0.0:{{ .Values.oauth2proxy.port }}
        - --cookie-secure={{ .Values.oauth2proxy.cookieSecure }}
        - --redirect-url={{ .Values.oauth2proxy.redirectUrl }}
        - --skip-provider-button={{ .Values.oauth2proxy.skipProviderButton }}
        - --insecure-oidc-allow-unverified-email={{ .Values.oauth2proxy.insecureOidc }}
        - --ssl-insecure-skip-verify={{ .Values.oauth2proxy.sslInsecure }}
        - --skip-oidc-discovery={{ .Values.oauth2proxy.skipOidcDiscovery }}
        env:
        - name: OAUTH2_PROXY_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: {{ include "noah-common.fullname" . }}-oauth2-secrets
              key: client-secret
        - name: OAUTH2_PROXY_COOKIE_SECRET
          valueFrom:
            secretKeyRef:
              name: {{ include "noah-common.fullname" . }}-oauth2-secrets
              key: cookie-secret
        ports:
        - name: http
          containerPort: {{ .Values.oauth2proxy.port }}
          protocol: TCP
        {{- if .Values.oauth2proxy.resources }}
        resources:
          {{- toYaml .Values.oauth2proxy.resources | nindent 10 }}
        {{- end }}
{{- end }}

{{/*
OAuth2 Proxy service template
*/}}
{{- define "noah-common.oauth2.service" -}}
apiVersion: v1
kind: Service
metadata:
  name: {{ include "noah-common.fullname" . }}-oauth2-proxy
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "noah-common.oauth2.labels" . | nindent 4 }}
spec:
  type: {{ .Values.oauth2proxy.service.type }}
  ports:
  - port: {{ .Values.oauth2proxy.service.port }}
    targetPort: {{ .Values.oauth2proxy.port }}
    protocol: TCP
    name: http
  selector:
    {{- include "noah-common.oauth2.selectorLabels" . | nindent 4 }}
{{- end }}
