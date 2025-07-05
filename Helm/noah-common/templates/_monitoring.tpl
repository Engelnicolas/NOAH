{{/*
=====================================
NOAH Monitoring Templates
=====================================
Common ServiceMonitor and monitoring configurations
*/}}

{{/*
ServiceMonitor template
*/}}
{{- define "noah.serviceMonitor" -}}
{{- if .Values.serviceMonitor.enabled }}
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ include "noah.fullname" . }}
  namespace: {{ .Values.serviceMonitor.namespace | default .Release.Namespace }}
  labels:
    {{- include "noah.labels" . | nindent 4 }}
    {{- with .Values.serviceMonitor.labels }}
    {{- toYaml . | nindent 4 }}
    {{- end }}
spec:
  selector:
    matchLabels:
      {{- include "noah.selectorLabels" . | nindent 6 }}
  endpoints:
  - port: {{ .Values.serviceMonitor.port | default "http" }}
    interval: {{ .Values.serviceMonitor.interval | default "30s" }}
    path: {{ .Values.serviceMonitor.path | default "/metrics" }}
    {{- with .Values.serviceMonitor.scrapeTimeout }}
    scrapeTimeout: {{ . }}
    {{- end }}
    {{- with .Values.serviceMonitor.relabelings }}
    relabelings:
    {{- toYaml . | nindent 4 }}
    {{- end }}
    {{- with .Values.serviceMonitor.metricRelabelings }}
    metricRelabelings:
    {{- toYaml . | nindent 4 }}
    {{- end }}
{{- end }}
{{- end }}

{{/*
Prometheus Rule template
*/}}
{{- define "noah.prometheusRule" -}}
{{- if .Values.prometheusRule.enabled }}
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: {{ include "noah.fullname" . }}
  namespace: {{ .Values.prometheusRule.namespace | default .Release.Namespace }}
  labels:
    {{- include "noah.labels" . | nindent 4 }}
    {{- with .Values.prometheusRule.labels }}
    {{- toYaml . | nindent 4 }}
    {{- end }}
spec:
  groups:
  - name: {{ include "noah.fullname" . }}.rules
    rules:
    - alert: {{ title (include "noah.name" .) }}Down
      expr: up{job="{{ include "noah.fullname" . }}"} == 0
      for: {{ .Values.prometheusRule.downtime | default "5m" }}
      labels:
        severity: critical
        service: {{ include "noah.name" . }}
      annotations:
        summary: "{{ title (include "noah.name" .) }} service is down"
        description: "{{ title (include "noah.name" .) }} service has been down for more than {{ .Values.prometheusRule.downtime | default "5m" }}"
    {{- with .Values.prometheusRule.additionalRules }}
    {{- toYaml . | nindent 4 }}
    {{- end }}
{{- end }}
{{- end }}

{{/*
Pod Monitor template
*/}}
{{- define "noah.podMonitor" -}}
{{- if .Values.podMonitor.enabled }}
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: {{ include "noah.fullname" . }}
  namespace: {{ .Values.podMonitor.namespace | default .Release.Namespace }}
  labels:
    {{- include "noah.labels" . | nindent 4 }}
    {{- with .Values.podMonitor.labels }}
    {{- toYaml . | nindent 4 }}
    {{- end }}
spec:
  selector:
    matchLabels:
      {{- include "noah.selectorLabels" . | nindent 6 }}
  podMetricsEndpoints:
  - port: {{ .Values.podMonitor.port | default "metrics" }}
    interval: {{ .Values.podMonitor.interval | default "30s" }}
    path: {{ .Values.podMonitor.path | default "/metrics" }}
    {{- with .Values.podMonitor.scrapeTimeout }}
    scrapeTimeout: {{ . }}
    {{- end }}
{{- end }}
{{- end }}
