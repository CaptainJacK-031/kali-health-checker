from app.analyzer import analyze

def test_analyzer_tolerates_missing_fields():
    s={"cpu":{"data":{}},"memory":{"data":{}},"storage":{"data":{}},"apt":{"data":{}},"services":{"data":{}},"logs":{"data":{}},"kernel_events":{"data":{}}}
    result=analyze(s)
    assert "findings" in result

def test_analyzer_does_not_keyerror_old_missing_fields():
    s={}
    result=analyze(s)
    assert result["overall"] in {"HEALTHY","WARNING","CRITICAL"}
