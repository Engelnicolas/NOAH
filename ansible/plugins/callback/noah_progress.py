#!/usr/bin/env python3
# NOAH Custom Callback Plugin for Detailed Progress
# Provides detailed, colored progress information during playbook execution

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import sys
import time
from ansible.plugins.callback import CallbackBase

# Simple color function
def colorize(msg, color=None):
    """Simple colorization function"""
    colors = {
        'green': '\033[92m',
        'red': '\033[91m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'reset': '\033[0m'
    }
    
    if color and color in colors:
        return f"{colors[color]}{msg}{colors['reset']}"
    return msg

DOCUMENTATION = '''
    callback: noah_progress
    type: stdout
    short_description: NOAH detailed progress callback
    description:
        - This callback provides detailed, colored progress information during NOAH playbook execution
        - Shows task progress with timestamps and status
        - Provides better visibility into long-running tasks
    version_added: "1.0"
    extends_documentation_fragment:
      - default_callback
    requirements:
      - Ansible 2.9+
'''

class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'noah_progress'

    def __init__(self):
        super(CallbackModule, self).__init__()
        self.task_start_time = {}
        self.play_start_time = None
        
    def _get_timestamp(self):
        return time.strftime("[%H:%M:%S]", time.localtime())
    
    def _colorize(self, text, color):
        return colorize(text, color)
    
    def v2_playbook_on_start(self, playbook):
        self._display.display("🚀 Démarrage du playbook NOAH: %s" % playbook._file_name)
        
    def v2_playbook_on_play_start(self, play):
        self.play_start_time = time.time()
        name = play.get_name().strip()
        self._display.display("\n" + "="*80)
        self._display.display("🎯 PHASE: %s" % self._colorize(name, 'cyan'))
        self._display.display("="*80)
        
    def v2_playbook_on_task_start(self, task, is_conditional):
        task_name = task.get_name().strip()
        self.task_start_time[task._uuid] = time.time()
        
        # Map des icônes pour différents types de tâches
        task_icons = {
            'install': '📦',
            'download': '⬇️',
            'create': '✨',
            'configure': '⚙️',
            'deploy': '🚀',
            'verify': '✅',
            'wait': '⏳',
            'copy': '📋',
            'add': '➕',
            'update': '🔄',
            'gathering facts': '📊'
        }
        
        # Déterminer l'icône basée sur le nom de la tâche
        icon = '🔧'
        for keyword, task_icon in task_icons.items():
            if keyword.lower() in task_name.lower():
                icon = task_icon
                break
                
        timestamp = self._get_timestamp()
        self._display.display("%s %s %s" % (
            self._colorize(timestamp, 'blue'),
            icon,
            self._colorize(task_name, 'yellow')
        ))
        
    def v2_runner_on_ok(self, result):
        task_uuid = result._task._uuid
        if task_uuid in self.task_start_time:
            duration = time.time() - self.task_start_time[task_uuid]
            timestamp = self._get_timestamp()
            
            # Afficher le résultat avec durée
            if duration > 1:
                self._display.display("%s   ✅ %s (%.1fs)" % (
                    self._colorize(timestamp, 'blue'),
                    self._colorize("Terminé", 'green'),
                    duration
                ))
            else:
                self._display.display("%s   ✅ %s" % (
                    self._colorize(timestamp, 'blue'),
                    self._colorize("Terminé", 'green')
                ))
                
            del self.task_start_time[task_uuid]
            
    def v2_runner_on_failed(self, result, ignore_errors=False):
        task_uuid = result._task._uuid
        timestamp = self._get_timestamp()
        
        if ignore_errors:
            self._display.display("%s   ⚠️  %s (ignoré)" % (
                self._colorize(timestamp, 'blue'),
                self._colorize("Échec", 'yellow')
            ))
        else:
            self._display.display("%s   ❌ %s" % (
                self._colorize(timestamp, 'blue'),
                self._colorize("ÉCHEC", 'red')
            ))
            
        if task_uuid in self.task_start_time:
            del self.task_start_time[task_uuid]
            
    def v2_runner_on_skipped(self, result):
        task_uuid = result._task._uuid
        timestamp = self._get_timestamp()
        
        self._display.display("%s   ⏭️  %s" % (
            self._colorize(timestamp, 'blue'),
            self._colorize("Ignoré", 'cyan')
        ))
        
        if task_uuid in self.task_start_time:
            del self.task_start_time[task_uuid]
            
    def v2_playbook_on_stats(self, stats):
        if self.play_start_time:
            total_duration = time.time() - self.play_start_time
            self._display.display("\n" + "="*80)
            self._display.display("📊 RÉSUMÉ DE LA CONFIGURATION")
            self._display.display("="*80)
            self._display.display("⏱️  Durée totale: %.1f secondes" % total_duration)
            
            # Statistiques par host
            hosts = sorted(stats.processed.keys())
            for host in hosts:
                host_stats = stats.summarize(host)
                self._display.display("🖥️  Host: %s" % self._colorize(host, 'cyan'))
                self._display.display("   ✅ Réussis: %d" % host_stats['ok'])
                if host_stats['failures'] > 0:
                    self._display.display("   ❌ Échecs: %d" % host_stats['failures'])
                if host_stats['skipped'] > 0:
                    self._display.display("   ⏭️  Ignorés: %d" % host_stats['skipped'])
                    
            self._display.display("="*80)
            
    def v2_runner_item_on_ok(self, result):
        # Pour les tâches avec loop, afficher l'item traité
        item = result._result.get('item', None)
        if item:
            timestamp = self._get_timestamp()
            self._display.display("%s     ↳ %s: %s" % (
                self._colorize(timestamp, 'blue'),
                self._colorize("✅", 'green'),
                str(item)
            ))
            
    def v2_runner_item_on_failed(self, result):
        item = result._result.get('item', None)
        if item:
            timestamp = self._get_timestamp()
            self._display.display("%s     ↳ %s: %s" % (
                self._colorize(timestamp, 'blue'),
                self._colorize("❌", 'red'),
                str(item)
            ))
