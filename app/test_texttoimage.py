import unittest
import texttoimage
from decouple import config

class TextToImageTest(unittest.TestCase):
    def _testTextToImage(self, textToImage):
        # arrange
        prompt = "a girl with green hair"

        # act
        images = textToImage.process(prompt)

        # assert
        self.assertIsNotNone(images)
        self.assertGreater(len(images), 0)
        for image in images:
            fileName, binary = image
            self.assertGreater(len(fileName), 0)
            self.assertGreater(len(binary), 20000)

    def test_stableHorde(self):
        textToImage = texttoimage.StableHordeTextToImage(config("STABLEHORDE_APIKEY"))
        self._testTextToImage(textToImage)
    
    def test_StableDiffusionAIOrg(self):
        textToImage = texttoimage.StableDiffusionAIOrg()
        self._testTextToImage(textToImage)

    @unittest.skip("No quota left on account")
    def test_Kandinsky2API(self):
        textToImage = texttoimage.Kandinsky2API()
        self._testTextToImage(textToImage)
    
    @unittest.skip("No quota left on account")
    def test_StableDiffusionAPI(self):
        textToImage = texttoimage.StableDiffusionAPI()
        self._testTextToImage(textToImage)
            

if __name__ == '__main__':
    unittest.main()

