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

    def test_remote_ollama_is_not_contacted_without_consent(self):
        client = LLMClient.__new__(LLMClient)
        client.provider = "ollama"
        client.client = None
        with patch.object(AIConfig, "OLLAMA_URL", "https://ollama.example.com"), patch.object(AIConfig, "OLLAMA_EXTERNAL_CONSENT", False), patch("app.ai.llm_client.requests.get") as get:
            self.assertFalse(client._ollama_disponivel())
        get.assert_not_called()

    def test_long_prompt_keeps_beginning_and_final_rules(self):
        prompt = "REGRAS_INICIAIS\n" + ("x" * 30000) + "\nREGRAS_FINAIS"

        with patch.object(AIConfig, "OLLAMA_MAX_PROMPT_CHARS", 12000):
            compact = LLMClient._compact_prompt(prompt)

        self.assertLessEqual(len(compact), 12100)
        self.assertIn("REGRAS_INICIAIS", compact)
        self.assertIn("REGRAS_FINAIS", compact)
