{{/*
Expand the name of the chart.
*/}}
{{- define "samba4.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "samba4.fullname" -}}
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
{{- define "samba4.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "samba4.labels" -}}
helm.sh/chart: {{ include "samba4.chart" . }}
{{ include "samba4.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "samba4.selectorLabels" -}}
app.kubernetes.io/name: {{ include "samba4.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "samba4.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "samba4.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use
*/}}
{{- define "samba4.secretName" -}}
{{- if .Values.existingSecret }}
{{- .Values.existingSecret }}
{{- else }}
{{- include "samba4.fullname" . }}
{{- end }}
{{- end }}

{{/*
Create the name of the configmap to use
*/}}
{{- define "samba4.configMapName" -}}
{{- if .Values.existingConfigMap }}
{{- .Values.existingConfigMap }}
{{- else }}
{{- include "samba4.fullname" . }}
{{- end }}
{{- end }}

{{/*
Generate Samba configuration
*/}}
{{- define "samba4.sambaConfig" -}}
[global]
    workgroup = {{ .Values.samba.workgroup | upper }}
    realm = {{ .Values.samba.realm | upper }}
    netbios name = {{ .Values.samba.netbiosName | upper }}
    server role = {{ .Values.samba.serverRole }}
    dns forwarder = {{ .Values.samba.dnsForwarder }}
    
    # Logging
    log level = {{ .Values.samba.logLevel | default 1 }}
    log file = /var/log/samba/log.%m
    max log size = {{ .Values.samba.maxLogSize | default 1000 }}
    
    # Security settings
    server min protocol = {{ .Values.samba.minProtocol | default "SMB2_10" }}
    server max protocol = {{ .Values.samba.maxProtocol | default "SMB3" }}
    client min protocol = {{ .Values.samba.clientMinProtocol | default "SMB2_10" }}
    client max protocol = {{ .Values.samba.clientMaxProtocol | default "SMB3" }}
    
    # TLS settings
    {{- if .Values.samba.tls.enabled }}
    tls enabled = yes
    tls keyfile = {{ .Values.samba.tls.keyFile }}
    tls certfile = {{ .Values.samba.tls.certFile }}
    tls cafile = {{ .Values.samba.tls.caFile }}
    {{- end }}
    
    # LDAP settings for AD
    ldap server require strong auth = {{ .Values.samba.ldap.requireStrongAuth | default "yes" }}
    
    # Performance tuning
    socket options = {{ .Values.samba.socketOptions | default "TCP_NODELAY IPTOS_LOWDELAY SO_RCVBUF=131072 SO_SNDBUF=131072" }}
    read raw = {{ .Values.samba.readRaw | default "yes" }}
    write raw = {{ .Values.samba.writeRaw | default "yes" }}
    max xmit = {{ .Values.samba.maxXmit | default 65536 }}
    
    # Misc settings
    load printers = {{ .Values.samba.loadPrinters | default "no" }}
    printing = {{ .Values.samba.printing | default "bsd" }}
    printcap name = /dev/null
    disable spoolss = {{ .Values.samba.disableSpoolss | default "yes" }}
    
    {{- with .Values.samba.extraGlobalConfig }}
    {{- toYaml . | nindent 4 }}
    {{- end }}

{{- range .Values.samba.shares }}
[{{ .name }}]
    {{- if .comment }}
    comment = {{ .comment }}
    {{- end }}
    path = {{ .path }}
    {{- if .readOnly }}
    read only = yes
    {{- else }}
    read only = no
    {{- end }}
    {{- if .browseable }}
    browseable = yes
    {{- else }}
    browseable = no
    {{- end }}
    {{- if .guestOk }}
    guest ok = yes
    {{- else }}
    guest ok = no
    {{- end }}
    {{- if .validUsers }}
    valid users = {{ join " " .validUsers }}
    {{- end }}
    {{- if .writeList }}
    write list = {{ join " " .writeList }}
    {{- end }}
    {{- if .createMask }}
    create mask = {{ .createMask }}
    {{- end }}
    {{- if .directoryMask }}
    directory mask = {{ .directoryMask }}
    {{- end }}
    {{- with .extraConfig }}
    {{- toYaml . | nindent 4 }}
    {{- end }}

{{- end }}
{{- end }}

{{/*
Generate Kerberos configuration
*/}}
{{- define "samba4.krb5Config" -}}
[libdefaults]
    default_realm = {{ .Values.samba.realm | upper }}
    dns_lookup_realm = {{ .Values.kerberos.dnsLookupRealm | default "true" }}
    dns_lookup_kdc = {{ .Values.kerberos.dnsLookupKdc | default "true" }}
    ticket_lifetime = {{ .Values.kerberos.ticketLifetime | default "24h" }}
    renew_lifetime = {{ .Values.kerberos.renewLifetime | default "7d" }}
    forwardable = {{ .Values.kerberos.forwardable | default "true" }}

[realms]
    {{ .Values.samba.realm | upper }} = {
        kdc = {{ include "samba4.fullname" . }}.{{ .Release.Namespace }}.svc.cluster.local
        admin_server = {{ include "samba4.fullname" . }}.{{ .Release.Namespace }}.svc.cluster.local
        default_domain = {{ .Values.samba.realm | lower }}
    }

[domain_realm]
    .{{ .Values.samba.realm | lower }} = {{ .Values.samba.realm | upper }}
    {{ .Values.samba.realm | lower }} = {{ .Values.samba.realm | upper }}

{{- with .Values.kerberos.extraConfig }}
{{- toYaml . | nindent 0 }}
{{- end }}
{{- end }}

{{/*
Generate DNS zone configuration
*/}}
{{- define "samba4.dnsZones" -}}
{{- range .Values.dns.zones }}
zone "{{ .name }}" {
    type master;
    file "/var/lib/samba/private/dns/{{ .name }}.zone";
    allow-update { key "rndc. {{ $.Values.samba.realm | upper }}"; };
};
{{- end }}
{{- end }}

{{/*
Create backup script
*/}}
{{- define "samba4.backupScript" -}}
#!/bin/bash
set -e

BACKUP_DIR="/backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REALM="{{ .Values.samba.realm | upper }}"

echo "Starting Samba4 AD backup at $(date)"

# Create AD backup
echo "Creating AD database backup..."
samba-tool domain backup offline --targetdir=${BACKUP_DIR}/ad_${TIMESTAMP}

# Backup sysvol
echo "Backing up sysvol..."
tar -czf ${BACKUP_DIR}/sysvol_${TIMESTAMP}.tar.gz /var/lib/samba/sysvol/

# Backup configuration
echo "Backing up configuration..."
tar -czf ${BACKUP_DIR}/config_${TIMESTAMP}.tar.gz /etc/samba/

{{- if .Values.backup.s3.enabled }}
# Upload to S3
echo "Uploading to S3..."
aws s3 sync ${BACKUP_DIR}/ s3://{{ .Values.backup.s3.bucket }}/samba4/ --region {{ .Values.backup.s3.region }}
{{- end }}

# Cleanup old backups
find ${BACKUP_DIR} -name "ad_*" -type d -mtime +{{ .Values.backup.retentionDays | default 30 }} -exec rm -rf {} \;
find ${BACKUP_DIR} -name "*.tar.gz" -mtime +{{ .Values.backup.retentionDays | default 30 }} -delete

echo "Backup completed successfully at $(date)"
{{- end }}
