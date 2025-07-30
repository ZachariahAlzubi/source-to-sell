import pytest
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("OPENAI_API_KEY", "test")
from services import LLMService, CompanyProfile

service = LLMService()

valid_json = '{"company_name":"Acme","industry":"Tech","size_hint":"50-100","products":[],"pain_points":[],"recent_events":[],"claims":[{"text":"test","source_url":null,"evidence_quote":null,"confidence":0.2}]}'

whitespace_json = '\n  ' + valid_json + '  \n'

fenced_json = '```json\n' + valid_json + '\n```'

garbage = 'not json at all'

@pytest.mark.parametrize('text', [valid_json, whitespace_json, fenced_json])
def test_parse_profile_ok(text):
    profile = service._parse_profile_json(text)
    assert isinstance(profile, CompanyProfile)
    assert profile.company_name == "Acme"


def test_parse_profile_fail():
    with pytest.raises(Exception):
        service._parse_profile_json(garbage)
