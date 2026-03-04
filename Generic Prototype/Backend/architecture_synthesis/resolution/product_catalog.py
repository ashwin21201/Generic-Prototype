import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from .product_schemas import ProductCatalog, Product

logger = logging.getLogger(__name__)


class ProductCatalogStore:
    """Store for product catalogs from multiple providers"""
    
    def __init__(self, catalogs_base_path: str = "products"):
        self.catalogs_base_path = Path(catalogs_base_path)
        self._catalogs: Dict[str, ProductCatalog] = {}
    
    def load_catalogs(self, provider_names: Optional[List[str]] = None):
        """
        Load product catalogs for specified providers.
        
        Args:
            provider_names: List of provider names (e.g., ["aws", "your_cloud"])
                           If None, loads all catalogs found
        """
        if provider_names is None:
            # Load all catalog files
            provider_names = self._discover_catalogs()
        
        for provider in provider_names:
            catalog = self._load_catalog(provider)
            if catalog:
                self._catalogs[provider] = catalog
                logger.info(f"Loaded catalog for {provider} with {len(catalog.products)} products")
    
    def _discover_catalogs(self) -> List[str]:
        """Discover all available catalog files"""
        providers = []
        if self.catalogs_base_path.exists():
            for file_path in self.catalogs_base_path.glob("*_catalog.json"):
                provider = file_path.stem.replace("_catalog", "")
                providers.append(provider)
        return providers
    
    def _load_catalog(self, provider: str) -> Optional[ProductCatalog]:
        """Load a single provider catalog"""
        catalog_file = self.catalogs_base_path / f"{provider}_catalog.json"
        
        try:
            if not catalog_file.exists():
                logger.warning(f"Catalog file not found: {catalog_file}")
                return None
            
            with open(catalog_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            catalog = ProductCatalog(**data)
            return catalog
            
        except Exception as e:
            logger.error(f"Error loading catalog {catalog_file}: {e}")
            return None
    
    def get_catalog(self, provider: str) -> Optional[ProductCatalog]:
        """Get catalog for a specific provider"""
        return self._catalogs.get(provider)
    
    def get_all_catalogs(self) -> Dict[str, ProductCatalog]:
        """Get all loaded catalogs"""
        return self._catalogs
    
    def find_products_by_capability(
        self,
        capability: str,
        provider: Optional[str] = None
    ) -> List[Product]:
        """Find products that provide a specific capability"""
        products = []
        
        catalogs_to_search = [self._catalogs[provider]] if provider else self._catalogs.values()
        
        for catalog in catalogs_to_search:
            for product in catalog.products:
                if product.capabilities.get(capability):
                    products.append(product)
        
        return products
    
    def find_products_by_category(
        self,
        category: str,
        provider: Optional[str] = None
    ) -> List[Product]:
        """Find products in a specific category"""
        products = []
        
        catalogs_to_search = [self._catalogs[provider]] if provider else self._catalogs.values()
        
        for catalog in catalogs_to_search:
            for product in catalog.products:
                if product.category == category:
                    products.append(product)
        
        return products
