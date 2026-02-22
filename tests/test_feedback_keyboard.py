import unittest

from inn_check_bot.main import _after_result_keyboard


class FeedbackKeyboardTests(unittest.TestCase):
    def test_after_result_keyboard_contains_feedback_buttons_with_inn(self):
        keyboard = _after_result_keyboard('7707083893').inline_keyboard

        self.assertEqual(keyboard[0][0].callback_data, 'feedback:helpful:7707083893')
        self.assertEqual(keyboard[0][1].callback_data, 'feedback:not_helpful:7707083893')
        self.assertEqual(keyboard[1][0].callback_data, 'check_another')


if __name__ == '__main__':
    unittest.main()
