import unittest
import paywall

class PaywallTests(unittest.TestCase):
    def _test_is_paywalled(self, link: str):
        # arrange
        pu = paywall.PageUnlocker(link)

        # act
        is_paywall = pu.is_paywalled()

        #assert
        self.assertTrue(is_paywall)

    def _test_is_not_paywalled(self, link: str):
        # arrange
        pu = paywall.PageUnlocker(link)

        # act
        is_paywall = pu.is_paywalled()

        #assert
        self.assertFalse(is_paywall)

    def test_paywalled(self):
        self._test_is_paywalled("https://www.faz.net/aktuell/finanzen/meine-finanzen/mieten-und-wohnen/baukredit-hauskaeufer-nutzt-die-verrueckten-zinsen-18968253.html")
        self._test_is_paywalled("https://www.spiegel.de/kultur/tv/hart-aber-fair-ausgabe-zu-rammstein-protokoll-einer-entgleisung-a-722df077-a4a3-455f-9094-a23d0edf48ce")
        self._test_is_paywalled("https://www.bild.de/bild-plus/gewinnspiele/bildplus-aktion/bild-couponaktion-freier-eintritt-in-den-serengeti-park-83783612.bild.html")
        
    def test_not_paywalled(self):
        self._test_is_not_paywalled("https://www.faz.net/aktuell/politik/inland/faz-sommerempfang-2023-im-berliner-borchardt-18978604.html")
        self._test_is_not_paywalled("https://www.spiegel.de/wissenschaft/technik/verschollenes-tauchboot-titan-es-ist-wie-die-nadel-im-heuhaufen-a-1ae26117-5046-4ed1-ba49-78335ab82744")
        self._test_is_not_paywalled("https://www.bild.de/sport/fussball/nationalmannschaft/nationalmannschaft-flick-widerspricht-lierhaus-im-tv-sie-sprach-kritisch-84403082.bild.html")