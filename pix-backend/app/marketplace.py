class MarketplaceRegistry:
    def list_templates(self): return []
    def get_template(self, name): return None
_reg = MarketplaceRegistry()
def get_marketplace_registry(): return _reg
