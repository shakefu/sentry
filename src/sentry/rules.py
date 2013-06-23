"""
Rules apply either before an event gets stored, or immediately after.

Basic actions:

- I want to get notified when [X]
- I want to group events when [X]

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
# TODO: the input concepts would conflict with each other in the HTML


from django.utils.html import escape
from django.utils.datastructures import SortedDict
from django.utils.safestring import mark_safe


NOTIFY_ON_FIRST_SEEN = 1
NOTIFY_ON_REGRESSION = 2
NOTIFY_ON_RATE_CHANGE = 3


class Rule(object):
    action_label = None
    condition_label = None

    def before(self, event):
        # should this pass event or the data?
        return event

    def after(self, event, is_new, is_regression, **kwargs):
        pass

    def render(self, initial=None):
        return self.condition_label


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


class NotifyOnTimesSeenRule(NotifyRule):
    condition_label = 'an event is seen more than {input} times'

    def should_notify(self, event):
        return event.times_seen == self.get_option('num')

    def render(self, data):
        return mark_safe(self.condition_label.format(
            input='<input type="number" name="num" value="{num}" size="10">'.format(
                num=escape(data.get('num', '1'))
            )
        ))

RULES = SortedDict(
    ('%s.%s' % (k.__module__, k.__name__), k) for k in [
        NotifyOnFirstSeenRule,
        NotifyOnRegressionRule,
        NotifyOnTimesSeenRule,
    ]
)
