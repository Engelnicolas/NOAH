{{/*
=====================================
NOAH Security Context Templates
=====================================
Common security configurations for all NOAH components
*/}}

{{/*
Pod Security Context - Default secure settings
*/}}
{{- define "noah.podSecurityContext" -}}
runAsNonRoot: true
runAsUser: {{ .Values.securityContext.runAsUser | default 1000 }}
runAsGroup: {{ .Values.securityContext.runAsGroup | default 1000 }}
fsGroup: {{ .Values.securityContext.fsGroup | default 1000 }}
{{- if .Values.securityContext.fsGroupChangePolicy }}
fsGroupChangePolicy: {{ .Values.securityContext.fsGroupChangePolicy }}
{{- end }}
seccompProfile:
  type: RuntimeDefault
{{- end }}

{{/*
Container Security Context - Default secure settings
*/}}
{{- define "noah.securityContext" -}}
runAsNonRoot: true
runAsUser: {{ .Values.securityContext.runAsUser | default 1000 }}
runAsGroup: {{ .Values.securityContext.runAsGroup | default 1000 }}
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
{{- if .Values.securityContext.readOnlyRootFilesystem }}
readOnlyRootFilesystem: true
{{- end }}
{{- end }}

{{/*
Network Policy - Default ingress rules
*/}}
{{- define "noah.networkPolicy.ingress" -}}
{{- if .Values.networkPolicy.enabled }}
- from:
  {{- if .Values.networkPolicy.allowedCIDRs }}
  {{- range .Values.networkPolicy.allowedCIDRs }}
  - ipBlock:
      cidr: {{ . }}
  {{- end }}
  {{- end }}
  {{- if .Values.networkPolicy.ingressNamespaces }}
  {{- range .Values.networkPolicy.ingressNamespaces }}
  - namespaceSelector:
      matchLabels:
        name: {{ . }}
  {{- end }}
  {{- end }}
  - namespaceSelector:
      matchLabels:
        name: {{ .Release.Namespace }}
  ports:
  {{- range .Values.service.ports }}
  - protocol: {{ .protocol | default "TCP" }}
    port: {{ .port }}
  {{- end }}
{{- end }}
{{- end }}

{{/*
Network Policy - Default egress rules
*/}}
{{- define "noah.networkPolicy.egress" -}}
{{- if .Values.networkPolicy.enabled }}
- to: []
  ports:
  - protocol: TCP
    port: 53
  - protocol: UDP
    port: 53
- to: []
  ports:
  - protocol: TCP
    port: 443
{{- if .Values.postgresql.enabled }}
- to:
  - namespaceSelector:
      matchLabels:
        name: {{ .Release.Namespace }}
  ports:
  - protocol: TCP
    port: 5432
{{- end }}
{{- if .Values.redis.enabled }}
- to:
  - namespaceSelector:
      matchLabels:
        name: {{ .Release.Namespace }}
  ports:
  - protocol: TCP
    port: 6379
{{- end }}
{{- end }}
{{- end }}
