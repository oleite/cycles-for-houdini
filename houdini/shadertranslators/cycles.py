import re

from husd.shadertranslator import ShaderTranslator
from husd.previewshadertranslator import PreviewShaderTranslator



class DefaultShaderTranslator( ShaderTranslator ):
    def __init__(self):
        ShaderTranslator.__init__(self)
        self.myPattern = re.compile( r'\bcycles\b' )

    def matchesRenderMask(self, render_mask):
        return bool( self.myPattern.search( render_mask ))


class DefaultPreviewShaderTranslator( PreviewShaderTranslator ):
    def __init__(self):
        PreviewShaderTranslator.__init__(self)

    def matchesRenderContext(self, render_context):
        return render_context == 'cycles'


default_translator = DefaultShaderTranslator()
def usdShaderTranslator():
    return default_translator


preview_translator = DefaultPreviewShaderTranslator()
def usdPreviewShaderTranslator():
    return preview_translator

