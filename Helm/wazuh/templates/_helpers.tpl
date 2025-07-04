{{/*
Expand the name of the chart.
*/}}
{{- define "wazuh.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "wazuh.fullname" -}}
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
{{- define "wazuh.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "wazuh.labels" -}}
helm.sh/chart: {{ include "wazuh.chart" . }}
{{ include "wazuh.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: noah
{{- end }}

{{/*
Selector labels for Wazuh Manager
*/}}
{{- define "wazuh.selectorLabels" -}}
app.kubernetes.io/name: {{ include "wazuh.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Selector labels for Wazuh Manager
*/}}
{{- define "wazuh.manager.selectorLabels" -}}
app.kubernetes.io/name: {{ include "wazuh.name" . }}-manager
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: manager
{{- end }}

{{/*
Selector labels for Wazuh Dashboard
*/}}
{{- define "wazuh.dashboard.selectorLabels" -}}
app.kubernetes.io/name: {{ include "wazuh.name" . }}-dashboard
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: dashboard
{{- end }}

{{/*
Selector labels for Wazuh Indexer
*/}}
{{- define "wazuh.indexer.selectorLabels" -}}
app.kubernetes.io/name: {{ include "wazuh.name" . }}-indexer
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: indexer
{{- end }}

{{/*
Selector labels for Wazuh Agent
*/}}
{{- define "wazuh.agent.selectorLabels" -}}
app.kubernetes.io/name: {{ include "wazuh.name" . }}-agent
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: agent
{{- end }}

{{/*
Create the name of the service account to use for Wazuh Manager
*/}}
{{- define "wazuh.manager.serviceAccountName" -}}
{{- if .Values.rbac.serviceAccount.create }}
{{- default (printf "%s-manager" (include "wazuh.fullname" .)) .Values.rbac.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.rbac.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the service account to use for Wazuh Dashboard
*/}}
{{- define "wazuh.dashboard.serviceAccountName" -}}
{{- if .Values.rbac.serviceAccount.create }}
{{- default (printf "%s-dashboard" (include "wazuh.fullname" .)) .Values.rbac.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.rbac.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the service account to use for Wazuh Indexer
*/}}
{{- define "wazuh.indexer.serviceAccountName" -}}
{{- if .Values.rbac.serviceAccount.create }}
{{- default (printf "%s-indexer" (include "wazuh.fullname" .)) .Values.rbac.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.rbac.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Generate certificates
*/}}
{{- define "wazuh.gen-certs" -}}
{{- $altNames := list ( printf "%s.%s" (include "wazuh.fullname" .) .Release.Namespace ) ( printf "%s.%s.svc" (include "wazuh.fullname" .) .Release.Namespace ) -}}
{{- $ca := genCA "wazuh-ca" 365 -}}
{{- $cert := genSignedCert ( include "wazuh.fullname" . ) nil $altNames 365 $ca -}}
tls.crt: {{ $cert.Cert | b64enc }}
tls.key: {{ $cert.Key | b64enc }}
ca.crt: {{ $ca.Cert | b64enc }}
{{- end }}

{{/*
Return the appropriate apiVersion for networkpolicy.
*/}}
{{- define "wazuh.networkPolicy.apiVersion" -}}
{{- if semverCompare ">=1.4-0" .Capabilities.KubeVersion.GitVersion -}}
{{- print "networking.k8s.io/v1" -}}
{{- else -}}
{{- print "extensions/v1beta1" -}}
{{- end -}}
{{- end -}}

{{/*
Return the appropriate apiVersion for poddisruptionbudget.
*/}}
{{- define "wazuh.podDisruptionBudget.apiVersion" -}}
{{- if semverCompare ">=1.21-0" .Capabilities.KubeVersion.GitVersion -}}
{{- print "policy/v1" -}}
{{- else -}}
{{- print "policy/v1beta1" -}}
{{- end -}}
{{- end -}}

{{/*
Return the appropriate apiVersion for HPA.
*/}}
{{- define "wazuh.hpa.apiVersion" -}}
{{- if semverCompare ">=1.23-0" .Capabilities.KubeVersion.GitVersion -}}
{{- print "autoscaling/v2" -}}
{{- else if semverCompare ">=1.12-0" .Capabilities.KubeVersion.GitVersion -}}
{{- print "autoscaling/v2beta2" -}}
{{- else -}}
{{- print "autoscaling/v2beta1" -}}
{{- end -}}
{{- end -}}

{{/*
Create a default fully qualified manager name.
*/}}
{{- define "wazuh.manager.fullname" -}}
{{- printf "%s-manager" (include "wazuh.fullname" .) -}}
{{- end -}}

{{/*
Create a default fully qualified dashboard name.
*/}}
{{- define "wazuh.dashboard.fullname" -}}
{{- printf "%s-dashboard" (include "wazuh.fullname" .) -}}
{{- end -}}

{{/*
Create a default fully qualified indexer name.
*/}}
{{- define "wazuh.indexer.fullname" -}}
{{- printf "%s-indexer" (include "wazuh.fullname" .) -}}
{{- end -}}

{{/*
Create a default fully qualified agent name.
*/}}
{{- define "wazuh.agent.fullname" -}}
{{- printf "%s-agent" (include "wazuh.fullname" .) -}}
{{- end -}}

{{/*
Generate random password if not provided
*/}}
{{- define "wazuh.password" -}}
{{- if . -}}
{{- . -}}
{{- else -}}
{{- randAlphaNum 20 -}}
{{- end -}}
{{- end -}}

{{/*
Create unified configuration for Wazuh Manager
*/}}
{{- define "wazuh.manager.config" -}}
ossec.conf: |
  <ossec_config>
    <global>
      <jsonout_output>yes</jsonout_output>
      <alerts_log>yes</alerts_log>
      <logall>no</logall>
      <logall_json>no</logall_json>
      <email_notification>{{ .Values.manager.config.email_notification.enabled }}</email_notification>
      <smtp_server>{{ .Values.manager.config.email_notification.smtp_server }}</smtp_server>
      <email_from>{{ .Values.manager.config.email_notification.email_from }}</email_from>
      <email_to>{{ .Values.manager.config.email_notification.email_to }}</email_to>
      <hostname>{{ include "wazuh.manager.fullname" . }}</hostname>
    </global>

    <alerts>
      <log_alert_level>3</log_alert_level>
      <email_alert_level>12</email_alert_level>
    </alerts>

    <remote>
      <connection>secure</connection>
      <port>{{ .Values.service.manager.ports | first | .port }}</port>
      <protocol>{{ .Values.agent.config.protocol }}</protocol>
      <allowed-ips>0.0.0.0/0</allowed-ips>
    </remote>

    {{- if .Values.manager.config.cluster.enabled }}
    <cluster>
      <name>{{ .Values.manager.config.cluster.node_name }}</name>
      <node_name>{{ .Values.manager.config.cluster.node_name }}</node_name>
      <node_type>{{ .Values.manager.config.cluster.node_type }}</node_type>
      <key>{{ .Values.manager.config.cluster.key }}</key>
      <port>{{ .Values.manager.config.cluster.port }}</port>
      <bind_addr>{{ .Values.manager.config.cluster.bind_addr }}</bind_addr>
      <nodes>
        <node>{{ include "wazuh.manager.fullname" . }}-0.{{ include "wazuh.manager.fullname" . }}-headless.{{ .Release.Namespace }}.svc.cluster.local</node>
        <node>{{ include "wazuh.manager.fullname" . }}-1.{{ include "wazuh.manager.fullname" . }}-headless.{{ .Release.Namespace }}.svc.cluster.local</node>
      </nodes>
      <hidden>{{ .Values.manager.config.cluster.hidden }}</hidden>
      <disabled>{{ .Values.manager.config.cluster.disabled }}</disabled>
    </cluster>
    {{- end }}

    {{- if .Values.manager.config.vulnerability_detector.enabled }}
    <vulnerability-detector>
      <enabled>{{ .Values.manager.config.vulnerability_detector.enabled }}</enabled>
      <interval>{{ .Values.manager.config.vulnerability_detector.interval }}</interval>
      <ignore_time>{{ .Values.manager.config.vulnerability_detector.ignore_time }}</ignore_time>
      <run_on_start>{{ .Values.manager.config.vulnerability_detector.run_on_start }}</run_on_start>
      {{- range .Values.manager.config.vulnerability_detector.providers }}
      <provider name="{{ . }}">
        <enabled>yes</enabled>
        <os>{{ . }}</os>
        <update_interval>1h</update_interval>
      </provider>
      {{- end }}
    </vulnerability-detector>
    {{- end }}

    {{- if .Values.manager.config.database_output.enabled }}
    <ossec_config>
      <database_output>
        <hostname>{{ .Values.manager.config.database_output.hosts | first }}</hostname>
        <username>{{ .Values.manager.config.database_output.username }}</username>
        <password>$(ELASTICSEARCH_PASSWORD)</password>
        <database>{{ .Values.manager.config.database_output.index_name }}</database>
      </database_output>
    </ossec_config>
    {{- end }}

    <ruleset>
      <decoder_dir>ruleset/decoders</decoder_dir>
      <rule_dir>ruleset/rules</rule_dir>
      <rule_exclude>0215-policy_rules.xml</rule_exclude>
      <list>etc/lists/audit-keys</list>
      <list>etc/lists/amazon/aws-eventnames</list>
      <list>etc/lists/security-eventchannel</list>
    </ruleset>

    <auth>
      <disabled>no</disabled>
      <port>1515</port>
      <use_source_ip>no</use_source_ip>
      <purge>yes</purge>
      <use_password>no</use_password>
      <ciphers>HIGH:!ADH:!EXP:!MD5:!RC4:!3DES:!CAMELLIA:@STRENGTH</ciphers>
      <ssl_agent_ca>/var/ossec/etc/rootca.pem</ssl_agent_ca>
      <ssl_verify_host>no</ssl_verify_host>
      <ssl_manager_cert>/var/ossec/etc/manager.cert</ssl_manager_cert>
      <ssl_manager_key>/var/ossec/etc/manager.key</ssl_manager_key>
      <ssl_auto_negotiate>no</ssl_auto_negotiate>
    </auth>

    {{- if .Values.manager.config.monitoring.enabled }}
    <monitoring>
      <enabled>{{ .Values.manager.config.monitoring.enabled }}</enabled>
      <frequency>{{ .Values.manager.config.monitoring.frequency }}</frequency>
      <compress>{{ .Values.manager.config.monitoring.compress }}</compress>
      <day_wait>{{ .Values.manager.config.monitoring.day_wait }}</day_wait>
    </monitoring>
    {{- end }}
  </ossec_config>
{{- end -}}

{{/*
Create unified configuration for Wazuh Dashboard
*/}}
{{- define "wazuh.dashboard.config" -}}
opensearch_dashboards.yml: |
  server.host: {{ .Values.dashboard.config.server.host }}
  server.port: {{ .Values.dashboard.config.server.port }}
  {{- if .Values.dashboard.config.server.ssl.enabled }}
  server.ssl.enabled: {{ .Values.dashboard.config.server.ssl.enabled }}
  server.ssl.certificate: {{ .Values.dashboard.config.server.ssl.certificate }}
  server.ssl.key: {{ .Values.dashboard.config.server.ssl.key }}
  {{- end }}
  
  opensearch.hosts: {{ .Values.dashboard.config.opensearch.hosts | toJson }}
  opensearch.username: {{ .Values.dashboard.config.opensearch.username }}
  opensearch.password: "$(OPENSEARCH_PASSWORD)"
  
  {{- if .Values.dashboard.config.opensearch.ssl }}
  opensearch.ssl.verificationMode: {{ .Values.dashboard.config.opensearch.ssl.verificationMode }}
  opensearch.ssl.certificateAuthorities: {{ .Values.dashboard.config.opensearch.ssl.certificateAuthorities | toJson }}
  {{- end }}
  
  wazuh.api.url: {{ .Values.dashboard.config.wazuh.api.url }}
  wazuh.api.port: {{ .Values.dashboard.config.wazuh.api.port }}
  wazuh.api.username: {{ .Values.dashboard.config.wazuh.api.username }}
  wazuh.api.password: "$(WAZUH_API_PASSWORD)"
  wazuh.api.run_as: {{ .Values.dashboard.config.wazuh.api.run_as }}
  
  {{- if .Values.dashboard.config.monitoring.enabled }}
  wazuh.monitoring.enabled: {{ .Values.dashboard.config.monitoring.enabled }}
  wazuh.monitoring.frequency: {{ .Values.dashboard.config.monitoring.frequency | default 900 }}
  wazuh.monitoring.shards: {{ .Values.dashboard.config.monitoring.shards | default 2 }}
  wazuh.monitoring.replicas: {{ .Values.dashboard.config.monitoring.replicas | default 0 }}
  {{- end }}
  
  logging.silent: {{ .Values.dashboard.config.logging.silent }}
  logging.quiet: {{ .Values.dashboard.config.logging.quiet }}
  logging.verbose: {{ .Values.dashboard.config.logging.verbose }}
  logging.dest: {{ .Values.dashboard.config.logging.dest }}
{{- end -}}
