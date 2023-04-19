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
            self.assertGreater(len(binary), 10000)

    def test_stableHorde(self):
        textToImage = texttoimage.StableHordeTextToImage(config("STABLEHORDE_APIKEY"))
        self._testTextToImage(textToImage)
    
    def test_StableDiffusionAIOrg(self):
        textToImage = texttoimage.StableDiffusionAIOrg()
        textToImage.setStoreFiles(True)
        self._testTextToImage(textToImage)
    
    def test_FallbackProcessor(self):
        # arrange
        class ExceptionImageProcessor(texttoimage.ImagePromptInterface):
            def process(self, prompt):
                raise Exception("fail")
        
        class NoneImageProcessor(texttoimage.ImagePromptInterface):
            def process(self, prompt):
                return None
            
        class GoodImageProcessor(texttoimage.ImagePromptInterface):
            def process(self, prompt):
                return [("bla.jpg", "x" * 50000)]
    
        processors = [ExceptionImageProcessor(), 
                      NoneImageProcessor(), 
                      GoodImageProcessor()]
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

