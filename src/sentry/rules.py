"""
Rules apply either before an event gets stored, or immediately after.

Basic actions:

- I want to get notified when [X]
- I want to group events when [X]
- I want to scrub data when [X]

Expanded:

- I want to get notified when an event is first seen
- I want to get notified when an event is marked as a regression
- I want to get notified when the rate of an event increases by [100%]
- I want to get notified when an event has been seen more than [100] times
- I want to get notified when an event matches [conditions]
- I want to group events when an event matches [conditions]

Rules get broken down into two phases:

- An action
- A rule condition

A condition itself may actually be any number of things, but that is determined
by the rule's logic. Each rule condition may be associated with a form.

- [ACTION:I want to get notified when] [RULE:an event is first seen]
- [ACTION:I want to group events when] [RULE:an event matches [FORM]]

"""
import re

from django import forms
from django.utils.html import escape
from django.utils.datastructures import SortedDict
from django.utils.safestring import mark_safe

from sentry.models import Rule as RuleModel


NOTIFY_ON_FIRST_SEEN = 1
NOTIFY_ON_REGRESSION = 2
NOTIFY_ON_RATE_CHANGE = 3


class RuleBase(type):
    def __new__(cls, *args, **kwargs):
        new_cls = super(RuleBase, cls).__new__(cls, *args, **kwargs)
        new_cls.id = '%s.%s' % (new_cls.__module__, new_cls.__name__)
        return new_cls


class Rule(object):
    __metaclass__ = RuleBase

    form_cls = None
    action_label = None
    condition_label = None

    @classmethod
    def from_params(cls, project, data=None):
        rule = RuleModel(
            project=project,
            data=data or {},
        )
        return cls(rule)

    def __init__(self, instance):
        self.instance = instance

    def before(self, event):
        # should this pass event or the data?
        return event

    def after(self, event, is_new, is_regression, **kwargs):
        pass

    def render_label(self):
        return ('%s %s' % (self.action_label, self.condition_label)).format(
            **self.instance.data)

    def render_form(self, form_data):
        if not self.form_cls:
            return self.condition_label

        form = self.form_cls(
            form_data,
            initial=self.instance.data,
            prefix=self.id,
        )

        def replace_field(match):
            field = match.group(1)
            return unicode(form[field])

        return mark_safe(re.sub(r'{([^}]+)}', replace_field, escape(self.condition_label)))

    def save(self, form_data):
        form = self.form_cls(
            form_data,
            initial=self.instance.data,
            prefix=self.id,
        )
        assert form.is_valid(), 'Form was not valid: %r' % (form.errors,)
        instance = self.instance
        instance.rule_id = self.id
        instance.data = form.cleaned_data
        instance.save()


class NotifyRule(Rule):
    action_label = 'I want to send notifications when'

    def notify(self, event):
        # TODO: fire off plugin notifications
        pass

    def after(self, event, **kwargs):
        if self.should_notify(event):
            self.notify(event)

    def should_notify(self, event):
        raise NotImplementedError


class NotifyOnFirstSeenRule(NotifyRule):
    condition_label = 'an event is first seen'

    def should_notify(self, event, is_new, **kwargs):
        return is_new


class NotifyOnRegressionRule(NotifyRule):
    condition_label = 'an event changes state from resolved to unresolved'

    def should_notify(self, event, is_regression, **kwargs):
        return is_regression


class NotifyOnTimesSeenForm(forms.Form):
    num = forms.IntegerField(widget=forms.TextInput(attrs={'type': 'number'}))


class NotifyOnTimesSeenRule(NotifyRule):
    form_cls = NotifyOnTimesSeenForm
    condition_label = 'an event is seen more than {num} times'

    def should_notify(self, event):
        return event.times_seen == self.get_option('num')


RULES = SortedDict(
    (k.id, k) for k in [
        NotifyOnFirstSeenRule,
        NotifyOnRegressionRule,
        NotifyOnTimesSeenRule,
    ]
)
