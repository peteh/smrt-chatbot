"""Tests for QuestionBots. """
import unittest
import smrt.bot.pipeline as pipeline

class PipelineHelperTests(unittest.TestCase):
    """Test Cases for Pipeline Helper functions"""
    def test_command_extraction_when_contains_only_bash_then_return_none(self):
        # arrange
        command_text = "#"

        # act
        return_data = pipeline.PipelineHelper.extract_command_full(command_text)

        # assert
        self.assertIsNone(return_data)
        
    def test_command_extraction_when_contains_only_bash_at_start_then_return_none(self):
        # arrange
        command_text = "# sdfd"

        # act
        return_data = pipeline.PipelineHelper.extract_command_full(command_text)

        # assert
        self.assertIsNone(return_data)

    def test_command_extraction_when_contains_params_then_extract_params(self):
        # arrange
        command_text = "#testcommand(parameters, params)"

        # act
        (command, params, text) = pipeline.PipelineHelper.extract_command_full(command_text)

        # assert
        self.assertEqual(command, "testcommand")
        self.assertEqual(params, "parameters, params")
        self.assertEqual(text, "")

    def test_command_with_dash_extraction_when_contains_params_then_extract_params(self):
        # arrange
        command_text = "#test_command(parameters, params)"

        # act
        (command, params, text) = pipeline.PipelineHelper.extract_command_full(command_text)

        # assert
        self.assertEqual(command, "test_command")
        self.assertEqual(params, "parameters, params")
        self.assertEqual(text, "")

    def test_command_extraction_when_contains_gpt3_prompt_then_extract_cmd_and_prompt(self):
        # arrange
        command_text = "#gpt3 Test prompt"

        # act
        (command, params, text) = pipeline.PipelineHelper.extract_command_full(command_text)

        # assert
        self.assertEqual(command, "gpt3")
        self.assertEqual(params, "")
        self.assertEqual(text, "Test prompt")

    def test_command_extraction_when_contains_only_text_then_extract_only_text(self):
        # arrange
        command_text = "#tinder lol ol oalsdsfdsd"

        # act
        (command, params, text) = pipeline.PipelineHelper.extract_command_full(command_text)

        # assert
        self.assertEqual(command, "tinder")
        self.assertEqual(params, "")
        self.assertEqual(text, "lol ol oalsdsfdsd")

    def test_command_extraction_when_only_command_then_extract_only_command(self):
        # arrange
        command_text = "#testcommand"

        # act
        (command, params, text) = pipeline.PipelineHelper.extract_command_full(command_text)

        # assert
        self.assertEqual(command, "testcommand")
        self.assertEqual(params, "")
        self.assertEqual(text, "")

    def test_command_extraction_when_no_command_then_return_none(self):
        # arrange
        command_text = "Just a random message"

        # act
        return_data = pipeline.PipelineHelper.extract_command_full(command_text)

        # assert
        self.assertIsNone(return_data)
        
        
if __name__ == '__main__':
    unittest.main()
