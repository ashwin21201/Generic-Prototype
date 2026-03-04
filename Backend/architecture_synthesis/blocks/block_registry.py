import json
import logging
from pathlib import Path
from typing import Optional, List, Dict
from .block_schemas import BlockRegistry, BlockDefinition

logger = logging.getLogger(__name__)


class BlockRegistryStore:
    """Read-only access to block definitions"""
    
    def __init__(self, registry_path: str = "blocks/block_registry.json"):
        self.registry_path = Path(registry_path)
        self._registry: Optional[BlockRegistry] = None
        self._blocks_by_id: Dict[str, BlockDefinition] = {}
        self._blocks_by_category: Dict[str, List[BlockDefinition]] = {}
        
    def load(self):
        """Load the block registry from file"""
        try:
            if not self.registry_path.exists():
                raise FileNotFoundError(f"Block registry not found: {self.registry_path}")
            
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._registry = BlockRegistry(**data)
            
            # Build indexes
            self._blocks_by_id = {block.block_id: block for block in self._registry.blocks}
            
            self._blocks_by_category = {}
            for block in self._registry.blocks:
                if block.category not in self._blocks_by_category:
                    self._blocks_by_category[block.category] = []
                self._blocks_by_category[block.category].append(block)
            
            logger.info(f"Loaded {len(self._registry.blocks)} blocks from registry")
            
        except Exception as e:
            logger.error(f"Error loading block registry: {e}")
            raise
    
    def get_block(self, block_id: str) -> Optional[BlockDefinition]:
        """Get a block by ID"""
        if not self._registry:
            self.load()
        return self._blocks_by_id.get(block_id)
    
    def get_blocks_by_category(self, category: str) -> List[BlockDefinition]:
        """Get all blocks in a category"""
        if not self._registry:
            self.load()
        result = self._blocks_by_category.get(category, [])
        logger.debug(f"Found {len(result)} blocks in category '{category}': {[b.block_id for b in result]}")
        return result
    
    def get_all_blocks(self) -> List[BlockDefinition]:
        """Get all blocks"""
        if not self._registry:
            self.load()
        return self._registry.blocks
    
    def find_blocks_by_capability(self, capability: str, value: bool = True) -> List[BlockDefinition]:
        """Find blocks that provide a specific capability"""
        if not self._registry:
            self.load()
        
        matching_blocks = []
        for block in self._registry.blocks:
            if block.capabilities_provided.get(capability) == value:
                matching_blocks.append(block)
        
        return matching_blocks
    
    def find_blocks_by_capabilities(self, capabilities: Dict[str, bool]) -> List[BlockDefinition]:
        """Find blocks that provide all specified capabilities"""
        if not self._registry:
            self.load()
        
        matching_blocks = []
        for block in self._registry.blocks:
            matches_all = True
            for cap, required_value in capabilities.items():
                if block.capabilities_provided.get(cap) != required_value:
                    matches_all = False
                    break
            
            if matches_all:
                matching_blocks.append(block)
        
        return matching_blocks
