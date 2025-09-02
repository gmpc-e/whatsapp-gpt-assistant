from app.models import IntentResult

def test_intentresult_accepts_minimal_stub():
    # should not raise ValidationError
    r = IntentResult(intent="EVENT_UPDATE")
    assert r.intent == "EVENT_UPDATE"
    assert r.answer == ""
    assert r.event is None