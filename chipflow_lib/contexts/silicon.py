class SiliconContext:
    def __init__(self, config, platform):
        self.platform = platform

    def build(self):
        self.platform.build()
