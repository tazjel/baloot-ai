import pytest
import os
import json
from unittest.mock import MagicMock, patch
from ai_worker.llm_client import GeminiClient

# MOCK RESPONSE FOR SCENARIO
MOCK_SCENARIO_JSON = {
    "players": [{"name": "Me", "position": "Bottom", "hand": [{"rank":"A","suit":"S"}]}],
    "phase": "Playing",
    "correct_move": "AS"
}

# MOCK RESPONSE FOR MATCH ANALYSIS
MOCK_ANALYSIS_JSON = {
    "summary": "Good game.",
    "moments": [{"round": 1, "action": "Play AS", "critique": "Solid."}]
}

@patch('google.generativeai.GenerativeModel')
def test_generate_scenario_from_text(mock_model_cls):
    # Setup Mock
    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(MOCK_SCENARIO_JSON)
    mock_instance.generate_content.return_value = mock_response
    mock_model_cls.return_value = mock_instance

    client = GeminiClient(api_key="TEST_KEY")
    result = client.generate_scenario_from_text("I have Ace of Spades")
    
    assert result['players'][0]['hand'][0]['rank'] == 'A'
    assert "Act as a Baloot Scenario Builder" in mock_instance.generate_content.call_args[0][0]

@patch('google.generativeai.GenerativeModel')
def test_analyze_match_history(mock_model_cls):
    # Setup Mock
    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(MOCK_ANALYSIS_JSON)
    mock_instance.generate_content.return_value = mock_response
    mock_model_cls.return_value = mock_instance

    client = GeminiClient(api_key="TEST_KEY")
    dummy_history = [{"round": 1}]
    result = client.analyze_match_history(dummy_history)
    
    assert result['summary'] == "Good game."
    assert "Analyze this full Baloot Match History" in mock_instance.generate_content.call_args[0][0]
