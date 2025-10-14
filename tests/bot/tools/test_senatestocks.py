"""Tests for QuestionBots. """
import unittest
import smrt.bot.tools.senate_stocks as senate_stocks

class SenateStockTests(unittest.TestCase):

    def test_ticker_expansion_when_ticker_existsts_then_expand(self):
        # arrange
        ticker = "AAPL"

        # act
        stock_info = senate_stocks.StockInfo()
        expanded = stock_info.expand_symbol(ticker)
        print(expanded)

        # assert
        self.assertEqual(expanded, "AAPL (Apple Inc., Consumer Electronics)")
        
    def test_ticker_expansion_when_ticker_not_existsts_then_dont_expand(self):
        # arrange
        ticker = "RANDOMSHIT"

        # act
        stock_info = senate_stocks.StockInfo()
        expanded = stock_info.expand_symbol(ticker)

        # assert
        self.assertEqual(expanded, ticker)
        
if __name__ == '__main__':
    unittest.main()
