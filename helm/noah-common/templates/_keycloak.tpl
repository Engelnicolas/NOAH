{{/*
Keycloak common labels
*/}}
{{- define "noah-common.keycloak.labels" -}}
app.kubernetes.io/name: keycloak
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: keycloak
app.kubernetes.io/part-of: noah
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Keycloak selector labels
*/}}
{{- define "noah-common.keycloak.selectorLabels" -}}
app.kubernetes.io/name: keycloak
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Keycloak deployment template
*/}}
{{- define "noah-common.keycloak.deployment" -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "noah-common.fullname" . }}-keycloak
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "noah-common.keycloak.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.keycloak.replicaCount | default 1 }}
  selector:
    matchLabels:
      {{- include "noah-common.keycloak.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "noah-common.keycloak.selectorLabels" . | nindent 8 }}
    spec:
      containers:
      - name: keycloak
        image: "{{ .Values.keycloak.image.repository }}:{{ .Values.keycloak.image.tag }}"
        args:
        {{- range .Values.keycloak.args }}
        - {{ . }}
        {{- end }}
        env:
        {{- range $key, $value := .Values.keycloak.env }}
        - name: {{ $key }}
          value: "{{ $value }}"
        {{- end }}
        ports:
        - name: http
          containerPort: {{ .Values.keycloak.port }}
          protocol: TCP
        readinessProbe:
          httpGet:
            path: {{ .Values.keycloak.readinessProbe.path }}
            port: {{ .Values.keycloak.port }}
          initialDelaySeconds: {{ .Values.keycloak.readinessProbe.initialDelaySeconds }}
          periodSeconds: {{ .Values.keycloak.readinessProbe.periodSeconds }}
          timeoutSeconds: {{ .Values.keycloak.readinessProbe.timeoutSeconds }}
        livenessProbe:
          httpGet:
            path: {{ .Values.keycloak.livenessProbe.path }}
            port: {{ .Values.keycloak.port }}
          initialDelaySeconds: {{ .Values.keycloak.livenessProbe.initialDelaySeconds }}
          periodSeconds: {{ .Values.keycloak.livenessProbe.periodSeconds }}
          timeoutSeconds: {{ .Values.keycloak.livenessProbe.timeoutSeconds }}
        {{- if .Values.keycloak.resources }}
        resources:
          {{- toYaml .Values.keycloak.resources | nindent 10 }}
        {{- end }}
{{- end }}

{{/*
Keycloak service template
*/}}
{{- define "noah-common.keycloak.service" -}}
apiVersion: v1
kind: Service
metadata:
  name: {{ include "noah-common.fullname" . }}-keycloak
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "noah-common.keycloak.labels" . | nindent 4 }}
spec:
  type: {{ .Values.keycloak.service.type }}
  ports:
  - port: {{ .Values.keycloak.service.port }}
    targetPort: {{ .Values.keycloak.port }}
    protocol: TCP
    name: http
  selector:
    {{- include "noah-common.keycloak.selectorLabels" . | nindent 4 }}
{{- end }}

{{/*
Keycloak ConfigMap template
*/}}
{{- define "noah-common.keycloak.configmap" -}}
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "noah-common.fullname" . }}-keycloak-realm-import
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "noah-common.keycloak.labels" . | nindent 4 }}
data:
  realm-config.json: |
    {{- .Values.keycloak.realmConfig | toJson | nindent 4 }}
{{- end }}
