"""
sentry.web.frontend.projects.rules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2012 by the Sentry Team, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""
import re
from collections import defaultdict

from django.contrib import messages
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_protect

from sentry.constants import MEMBER_OWNER
from sentry.models import Rule
from sentry.utils import json
from sentry.utils.cache import memoize
from sentry.web.decorators import has_access
from sentry.web.helpers import render_to_response


class RuleFormValidator(object):
    # XXX(dcramer): please no judgements on any of the rule code, I realize it's
    # all terrible and poorly described
    def __init__(self, project, data=None):
        from sentry.rules import RULES

        self.project = project
        self.data = data
        self.rules = RULES['events']
        self.errors = {}

    @memoize
    def cleaned_data(self):
        # parse out rules
        rules_by_id = {
            'actions': {},
            'conditions': {},
        }
        for node in self.rules['conditions']:
            rules_by_id['conditions'][node.id] = node
        for node in self.rules['actions']:
            rules_by_id['actions'][node.id] = node

        key_regexp = r'^(condition|action)\[(\d+)\]\[(.+)\]$'
        raw_data = defaultdict(lambda: defaultdict(dict))
        for key, value in self.data.iteritems():
            match = re.match(key_regexp, key)
            if not match:
                continue
            raw_data[match.group(1)][match.group(2)][match.group(3)] = value

        data = {
            'label': self.data.get('label', '').strip(),
            'action_match': self.data.get('action_match', 'all'),
            'actions': [],
            'conditions': [],
        }

        for num, node in sorted(raw_data['condition'].iteritems()):
            data['conditions'].append(node)
            cls = rules_by_id['conditions'][node['id']]
            if not cls(self.project, node).validate_form():
                self.errors['condition[%s]' % (num,)] = 'Ensure all fields are filled out correctly.'

        for num, node in sorted(raw_data['action'].iteritems()):
            data['actions'].append(node)
            cls = rules_by_id['actions'][node['id']]
            if not cls(self.project, node).validate_form():
                self.errors['action[%s]' % (num,)] = 'Ensure all fields are filled out correctly.'

        if not data['label'] or len(data['label']) > 64:
            self.errors['label'] = 'Value must be less than 64 characters.'

        return data

    def is_valid(self):
        # force validation
        self.cleaned_data
        return not bool(self.errors)


@has_access(MEMBER_OWNER)
def list_rules(request, team, project):
    rule_list = Rule.objects.filter(project=project)

    context = csrf(request)
    context.update({
        'team': team,
        'page': 'rules',
        'project': project,
        'rule_list': rule_list,
    })

    return render_to_response('sentry/projects/rules/list.html', context, request)


@has_access(MEMBER_OWNER)
@csrf_protect
def create_or_edit_rule(request, team, project, rule_id=None):
    from sentry.rules import RULES

    if rule_id:
        rule = Rule.objects.get(project=project, id=rule_id)
    else:
        rule = Rule(project=project)

    rules = RULES['events']

    form_data = {
        'label': rule.label,
        'action_match': rule.data.get('action_match'),
    }

    for num, node in enumerate(rule.data.get('conditions', [])):
        prefix = 'condition[%d]' % (num,)
        for key, value in node.iteritems():
            form_data[prefix + '[' + key + ']'] = value

    for num, node in enumerate(rule.data.get('actions', [])):
        prefix = 'action[%d]' % (num,)
        for key, value in node.iteritems():
            form_data[prefix + '[' + key + ']'] = value

    for key, value in request.POST.iteritems():
        form_data[key] = value

    validator = RuleFormValidator(project, form_data)
    if request.POST and validator.is_valid():
        data = validator.cleaned_data.copy()

        rule.label = data.pop('label')
        rule.data = data
        rule.save()

        messages.add_message(
            request, messages.SUCCESS,
            _('Changes to your rule were saved.'))

        path = reverse('sentry-project-rules', args=[team.slug, project.slug])
        return HttpResponseRedirect(path)

    action_list = []
    condition_list = []

    for cls in rules['actions']:
        node = cls(project)
        action_list.append({
            'id': node.id,
            'label': node.label,
            'html': node.render_form(),
        })

    for cls in rules['conditions']:
        node = cls(project)
        condition_list.append({
            'id': node.id,
            'label': node.label,
            'html': node.render_form(),
        })

    context = csrf(request)
    context.update({
        'rule': rule,
        'form_is_valid': (not request.POST or validator.is_valid()),
        'form_errors': validator.errors,
        'form_data': form_data,
        'team': team,
        'page': 'rules',
        'action_list': json.dumps(action_list),
        'condition_list': json.dumps(condition_list),
        'project': project,
    })

    return render_to_response('sentry/projects/rules/new.html', context, request)
