import logging
from typing import List, Tuple, Set
from .block_schemas import BlockDefinition
from .block_registry import BlockRegistryStore

logger = logging.getLogger(__name__)


class CompatibilityWarning:
    """Warning about compatibility issues"""
    def __init__(self, message: str, severity: str = "warning"):
        self.message = message
        self.severity = severity


class CompatibilityResolver:
    """Resolve block dependencies and conflicts"""
    
    def __init__(self, block_registry: BlockRegistryStore):
        self.block_registry = block_registry
    
    def resolve(
        self,
        selected_block_ids: List[str]
    ) -> Tuple[List[BlockDefinition], List[CompatibilityWarning]]:
        """
        Resolve dependencies and conflicts for selected blocks.
        
        Args:
            selected_block_ids: List of block IDs
            
        Returns:
            Tuple of (resolved block definitions, warnings)
        """
        logger.info(f"Resolving compatibility for {len(selected_block_ids)} blocks")
        
        warnings = []
        resolved_ids = set(selected_block_ids)
        
        # Step 1: Resolve dependencies (add missing required blocks)
        resolved_ids, dep_warnings = self._resolve_dependencies(resolved_ids)
        warnings.extend(dep_warnings)
        
        # Step 2: Check and resolve conflicts
        resolved_ids, conflict_warnings = self._resolve_conflicts(resolved_ids)
        warnings.extend(conflict_warnings)
        
        # Step 3: Get block definitions
        resolved_blocks = []
        for block_id in resolved_ids:
            block = self.block_registry.get_block(block_id)
            if block:
                resolved_blocks.append(block)
            else:
                warnings.append(CompatibilityWarning(
                    f"Block not found in registry: {block_id}",
                    severity="error"
                ))
        
        logger.info(f"Resolved to {len(resolved_blocks)} blocks with {len(warnings)} warnings")
        return resolved_blocks, warnings
    
    def _resolve_dependencies(
        self,
        block_ids: Set[str]
    ) -> Tuple[Set[str], List[CompatibilityWarning]]:
        """Add missing required dependencies"""
        warnings = []
        resolved = set(block_ids)
        added_any = True
        max_iterations = 10
        iteration = 0

        def _requirement_satisfied(requirement: str, resolved_ids: Set[str]) -> bool:
            """Return True if requirement is already satisfied by any selected block."""
            # Exact block id requirement
            if self.block_registry.get_block(requirement):
                return requirement in resolved_ids

            req = (requirement or "").lower()
            # Category layer requirements (e.g. network_layer, compute_layer)
            if req.endswith("_layer"):
                category = req.replace("_layer", "")
                for bid in resolved_ids:
                    b = self.block_registry.get_block(bid)
                    if b and (b.category or "").lower() == category:
                        return True
                return False

            # Network-ish requirements (e.g. private_network)
            if "network" in req:
                for bid in resolved_ids:
                    b = self.block_registry.get_block(bid)
                    if b and (b.category or "").lower() == "network":
                        return True
                return False

            return False
        
        # Iteratively add dependencies until no more are needed
        while added_any and iteration < max_iterations:
            added_any = False
            iteration += 1
            
            current_blocks = list(resolved)
            for block_id in current_blocks:
                block = self.block_registry.get_block(block_id)
                if not block:
                    continue
                
                # Check required dependencies
                for required_id in block.requires:
                    if _requirement_satisfied(required_id, resolved):
                        continue
                    # If not satisfied, try to add a block that satisfies it.
                    if required_id not in resolved:
                        # Need to add this dependency
                        # Try to find a block that satisfies this requirement
                        dep_block = self._find_dependency_block(required_id)
                        
                        if dep_block:
                            if dep_block.block_id not in resolved:
                                resolved.add(dep_block.block_id)
                                added_any = True
                                logger.info(f"Added required dependency: {dep_block.block_id} for {block_id}")
                                warnings.append(CompatibilityWarning(
                                    f"Added required block '{dep_block.block_id}' as dependency of '{block_id}'"
                                ))
                        else:
                            warnings.append(CompatibilityWarning(
                                f"Could not find block to satisfy requirement '{required_id}' for '{block_id}'",
                                severity="error"
                            ))
        
        if iteration >= max_iterations:
            warnings.append(CompatibilityWarning(
                "Dependency resolution reached maximum iterations",
                severity="warning"
            ))
        
        return resolved, warnings
    
    def _find_dependency_block(self, requirement: str) -> BlockDefinition:
        """Find a block that satisfies a requirement"""
        # First, try exact block_id match
        block = self.block_registry.get_block(requirement)
        if block:
            return block
        
        # Try to find by category or capability
        # For example, "network_layer" might match category "network"
        if "_layer" in requirement:
            category = requirement.replace("_layer", "")
            blocks = self.block_registry.get_blocks_by_category(category)
            if blocks:
                return blocks[0]
        
        # Try "private_network" - could be satisfied by any network block
        if "network" in requirement.lower():
            blocks = self.block_registry.get_blocks_by_category("network")
            if blocks:
                return blocks[0]
        
        return None
    
    def _resolve_conflicts(
        self,
        block_ids: Set[str]
    ) -> Tuple[Set[str], List[CompatibilityWarning]]:
        """Remove or replace conflicting blocks"""
        warnings = []
        resolved = set(block_ids)
        
        blocks = [self.block_registry.get_block(bid) for bid in block_ids]
        blocks = [b for b in blocks if b is not None]
        
        # Check each pair for conflicts
        for i, block1 in enumerate(blocks):
            for block2 in blocks[i+1:]:
                # Check if block1 conflicts with block2
                if block2.block_id in block1.conflicts_with:
                    # Conflict detected - remove the one with lower priority
                    # For now, keep the first one (could be more sophisticated)
                    if block2.block_id in resolved:
                        resolved.remove(block2.block_id)
                        warnings.append(CompatibilityWarning(
                            f"Removed '{block2.block_id}' due to conflict with '{block1.block_id}'",
                            severity="warning"
                        ))
                        logger.warning(f"Conflict: removed {block2.block_id} (conflicts with {block1.block_id})")
                
                # Check if block2 conflicts with block1
                if block1.block_id in block2.conflicts_with:
                    if block1.block_id in resolved:
                        resolved.remove(block1.block_id)
                        warnings.append(CompatibilityWarning(
                            f"Removed '{block1.block_id}' due to conflict with '{block2.block_id}'",
                            severity="warning"
                        ))
                        logger.warning(f"Conflict: removed {block1.block_id} (conflicts with {block2.block_id})")
        
        return resolved, warnings
