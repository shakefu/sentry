from sentry.rules import (
    FirstSeenEventCondition, RegressionEventCondition, TaggedEventCondition
)
from sentry.testutils import TestCase


class RuleTestCase(TestCase):
    rule_cls = None

    def get_rule(self, data=None):
        return self.rule_cls(
            project=self.project,
            data=data or {},
        )

    def assertPasses(self, rule, event=None, **kwargs):
        if event is None:
            event = self.event
        kwargs.setdefault('is_new', True)
        kwargs.setdefault('is_regression', True)
        assert rule.passes(event, **kwargs) is True

    def assertDoesNotPass(self, rule, event=None, **kwargs):
        if event is None:
            event = self.event
        kwargs.setdefault('is_new', True)
        kwargs.setdefault('is_regression', True)
        assert rule.passes(event, **kwargs) is False


class FirstSeenEventConditionTest(RuleTestCase):
    rule_cls = FirstSeenEventCondition

    def test_applies_correctly(self):
        rule = self.get_rule()

        self.assertPasses(rule, self.event, is_new=True)

        self.assertDoesNotPass(rule, self.event, is_new=False)


class RegressionEventConditionTest(RuleTestCase):
    rule_cls = RegressionEventCondition

    def test_applies_correctly(self):
        rule = self.get_rule()

        self.assertPasses(rule, self.event, is_regression=True)

        self.assertDoesNotPass(rule, self.event, is_regression=False)


class TaggedEventConditionTest(RuleTestCase):
    rule_cls = TaggedEventCondition

    def get_event(self):
        event = self.event
        event.data['tags'] = (
            ('logger', 'sentry.example'),
            ('logger', 'foo.bar'),
            ('notlogger', 'sentry.other.example'),
            ('notlogger', 'bar.foo.baz'),
        )
        return event

    def test_equals(self):
        event = self.get_event()
        rule = self.get_rule({
            'match': 'eq',
            'key': 'logger',
            'value': 'sentry.example',
        })
        self.assertPasses(rule, event)

        rule = self.get_rule({
            'match': 'eq',
            'key': 'logger',
            'value': 'sentry.other.example',
        })
        self.assertDoesNotPass(rule, event)

    def test_starts_with(self):
        event = self.get_event()
        rule = self.get_rule({
            'match': 'sw',
            'key': 'logger',
            'value': 'sentry.',
        })
        self.assertPasses(rule, event)

        rule = self.get_rule({
            'match': 'sw',
            'key': 'logger',
            'value': 'bar.',
        })
        self.assertDoesNotPass(rule, event)

    def test_ends_with(self):
        event = self.get_event()
        rule = self.get_rule({
            'match': 'ew',
            'key': 'logger',
            'value': '.example',
        })
        self.assertPasses(rule, event)

        rule = self.get_rule({
            'match': 'ew',
            'key': 'logger',
            'value': '.foo',
        })
        self.assertDoesNotPass(rule, event)

    def test_contains(self):
        event = self.get_event()
        rule = self.get_rule({
            'match': 'co',
            'key': 'logger',
            'value': 'sentry',
        })
        self.assertPasses(rule, event)

        rule = self.get_rule({
            'match': 'co',
            'key': 'logger',
            'value': 'bar.foo',
        })
        self.assertDoesNotPass(rule, event)
