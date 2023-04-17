import unittest
import texttoimage
from decouple import config

class TextToImageTest(unittest.TestCase):
    def _testTextToImage(self, textToImage):
        # arrange
        prompt = "Underwear party"

        # act
        images = textToImage.process(prompt)

        # assert
        self.assertIsNotNone(images)
        self.assertGreaterEqual(len(images), 1)
        for image in images:
            fileName, binary = image
            self.assertGreater(len(fileName), 0)
            self.assertGreater(len(binary), 20000)

    def test_stableHorde(self):
        textToImage = texttoimage.StableHordeTextToImage(config("STABLEHORDE_APIKEY"))
        self._testTextToImage(textToImage)
    
    def test_StableDiffusionAIOrg(self):
        textToImage = texttoimage.StableDiffusionAIOrg()
        textToImage.setStoreFiles(True)
        self._testTextToImage(textToImage)
    
    def test_FallbackProcessor(self):
        processors = [texttoimage.StableDiffusionAIOrg(), 
                      texttoimage.StableHordeTextToImage(config("STABLEHORDE_APIKEY"))]
        textToImage = texttoimage.FallbackTextToImageProcessor(processors)
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

