from sentry.rules import FirstSeenEventCondition
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
