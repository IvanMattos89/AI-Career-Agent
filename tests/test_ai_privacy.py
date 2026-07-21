import unittest
from unittest.mock import Mock, patch

from app.ai.config import AIConfig
from app.ai.llm_client import LLMClient


class AIPrivacyTest(unittest.TestCase):
    def test_openai_is_not_called_without_explicit_consent(self):
        client = LLMClient.__new__(LLMClient)
        client.provider = "openai"
        client.client = Mock()

        with patch.object(AIConfig, "OPENAI_DATA_CONSENT", False):
            with self.assertRaisesRegex(RuntimeError, "requer autorização"):
                client.perguntar("currículo com dados pessoais")

        client.client.chat.completions.create.assert_not_called()

    def test_ollama_timeout_keeps_connection_limit_short(self):
        with patch.object(AIConfig, "OLLAMA_CONNECT_TIMEOUT", 5), patch.object(AIConfig, "OLLAMA_TIMEOUT", 60):
            self.assertEqual(LLMClient._timeout(None), (5, 60))
            self.assertEqual(LLMClient._timeout(20), (5, 20))
