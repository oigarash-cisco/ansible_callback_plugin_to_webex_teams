from __future__ import (absolute_import, division, print_function)
from ansible.module_utils._text import to_text
from ansible.module_utils.urls import open_url
from ansible.template import Templar
__metaclass__ = type

from ansible.plugins.callback import CallbackBase
import json

class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'webexteams'
    CALLBACK_NEEDS_WHITELIST = False
    WEBEX_TOKEN = 'YOURWEBEXTOKEN'
    WEBEX_API_URL = 'https://api.ciscospark.com/v1/'


    def send_message(self, message):
        headers = {
            "Authorization": "Bearer {}".format(self.WEBEX_TOKEN),
            "Content-Type": 'application/json'
        }
        payload = {
            'toPersonEmail': self.destination,
            'markdown': message
        }
        data = json.dumps(payload)
        try:
            response = open_url(self.WEBEX_API_URL + '/messages',
                                headers=headers, data=data, validate_certs=False)
            return response.read()
        except Exception as e:
            self._display.warning(u'Could not submit message to Webex Team: %s' %
                                  to_text(e))

    def v2_playbook_on_start(self, playbook):
        self.playbook = playbook

    def v2_playbook_on_stats(self, stats):
        playbook = self.playbook
        play = playbook.get_plays()[-1]

        variable_manager = play.get_variable_manager()
        inventory_hosts = variable_manager._inventory.get_hosts()
        play_vars = variable_manager.get_vars(play=play)

        templar = Templar(playbook._loader, variables=play_vars)
        destination = play_vars.get('notify_webex_destination')

        if destination is None:
            self._display.warning(
                "notify_webex_destination was not provided. Disalbed webexteam Callback plugin")
            return
        self.destination = templar.template(destination)

        messages = list()

        hosts = sorted(stats.processed.keys())
        for hostname in hosts:
            s = stats.summarize(hostname)
            host = [h for h in inventory_hosts if h.name == hostname][0]
            host_vars = variable_manager.get_vars(play=play, host=host)
            templar = Templar(playbook._loader, variables=host_vars)
            if s['failures'] > 0 or s['unreachable'] > 0:
                message_failed = host_vars.get('notify_webex_when_failed', None)
                if message_failed:
                    messages.append(templar.template(message_failed))
            else:
                message_success = host_vars.get(
                    'notify_webex_when_success', None)
                if message_success:
                    messages.append(templar.template(message_success))

        message_finished = play_vars.get('notify_webex_when_finished', None)
        messages.append(templar.template(message_finished))
        if messages:
            self.send_message("\n\n".join(messages))
