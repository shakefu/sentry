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
from django.utils.safestring import mark_safe


class RuleDescriptor(type):
    def __new__(cls, *args, **kwargs):
        new_cls = super(RuleDescriptor, cls).__new__(cls, *args, **kwargs)
        new_cls.id = '%s.%s' % (new_cls.__module__, new_cls.__name__)
        return new_cls


class RuleBase(object):
    label = None
    form_cls = None

    __metaclass__ = RuleDescriptor

    def __init__(self, project, data=None):
        self.project = project
        self.data = data or {}

    def get_option(self, key):
        return self.data.get(key)

    def render_label(self):
        return self.label.format(**self.data)

    def render_form(self):
        if not self.form_cls:
            return self.label

        form = self.form_cls(
            self.data,
        )

        def replace_field(match):
            field = match.group(1)
            return unicode(form[field])

        return mark_safe(re.sub(r'{([^}]+)}', replace_field, escape(self.label)))

    def validate_form(self):
        if not self.form_cls:
            return True

        form = self.form_cls(
            self.data,
        )

        return form.is_valid()


class MatchType(object):
    EQUAL = 'eq'
    NOT_EQUAL = 'ne'
    STARTS_WITH = 'sw'
    ENDS_WITH = 'ew'
    CONTAINS = 'co'
    NOT_CONTAINS = 'nc'


class EventAction(RuleBase):
    def before(self, event):
        # should this pass event or the data?
        return event

    def after(self, event, is_new, is_regression, **kwargs):
        pass


class EventCondition(RuleBase):
    def passes(self, event, is_new, is_regression, **kwargs):
        raise NotImplementedError


class NotifyEventAction(EventAction):
    label = 'Send a notification'

    def notify(self, event):
        # TODO: fire off plugin notifications
        pass

    def after(self, event, **kwargs):
        if self.should_notify(event):
            self.notify(event)

    def passes(self, event, **kwargs):
        raise NotImplementedError


class FirstSeenEventCondition(EventCondition):
    label = 'An event is first seen'

    def passes(self, event, is_new, **kwargs):
        return is_new


class RegressionEventCondition(EventCondition):
    label = 'An event changes state from resolved to unresolved'

    def passes(self, event, is_regression, **kwargs):
        return is_regression


class TaggedEventForm(forms.Form):
    key = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'key'}))
    match = forms.ChoiceField(choices=(
        (MatchType.EQUAL, 'equals'),
        (MatchType.NOT_EQUAL, 'does not equal'),
        (MatchType.STARTS_WITH, 'starts with'),
        (MatchType.ENDS_WITH, 'ends with'),
        (MatchType.CONTAINS, 'contains'),
        (MatchType.NOT_CONTAINS, 'does not contain'),
    ))
    value = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'value'}))


class TaggedEventCondition(EventCondition):
    form_cls = TaggedEventForm
    label = 'An events tags match {key} {match} {value}'

    def passes(self, event, is_regression, **kwargs):
        key = self.get_option('key')
        match = self.get_option('match')
        value = self.get_option('value')

        tags = (v for k, v in event.get_tags() if k == key)

        if match == MatchType.EQUAL:
            for t_value in tags:
                if t_value == value:
                    return True
            return False

        elif match == MatchType.NOT_EQUAL:
            for t_value in tags:
                if t_value == value:
                    return False
            return True

        elif match == MatchType.STARTS_WITH:
            for t_value in tags:
                if t_value.startswith(value):
                    return True
            return False

        elif match == MatchType.ENDS_WITH:
            for t_value in tags:
                if t_value.endswith(value):
                    return True
            return False

        elif match == MatchType.CONTAINS:
            for t_value in tags:
                if value in t_value:
                    return True
            return False

        elif match == MatchType.NOT_CONTAINS:
            for t_value in tags:
                if value in t_value:
                    return False
            return True


# class TimesSeenEventForm(forms.Form):
#     num = forms.IntegerField(widget=forms.TextInput(attrs={'type': 'number'}))


# class TimesSeenEventCondition(EventCondition):
#     form_cls = TimesSeenEventForm
#     label = 'An event is seen more than {num} times'

#     def passes(self, event):
#         return event.times_seen == self.get_option('num')


RULES = {
    'events': {
        'actions': [
            NotifyEventAction,
        ],
        'conditions': [
            FirstSeenEventCondition,
            RegressionEventCondition,
            TaggedEventCondition,
        ],
    }
}
