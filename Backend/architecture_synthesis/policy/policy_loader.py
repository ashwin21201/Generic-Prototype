import json
import logging
from pathlib import Path
from typing import List, Optional
from .policy_schemas import PolicyJSON

logger = logging.getLogger(__name__)


class PolicyLoader:
    """Load policy files from the policies directory"""
    
    def __init__(self, policies_base_path: str = "policies"):
        self.policies_base_path = Path(policies_base_path)
        
    def load_policies(
        self,
        sector: str,
        region: Optional[str] = None,
        org_level: Optional[str] = None
    ) -> List[PolicyJSON]:
        """
        Load policies based on sector, region, and org level.
        
        Args:
            sector: Sector name (e.g., "BFSI", "healthcare")
            region: Optional region name (e.g., "India", "US")
            org_level: Optional organization-level policy name
            
        Returns:
            List of PolicyJSON objects
        """
        policies = []
        
        # Load sector policy
        sector_policy = self._load_sector_policy(sector)
        if sector_policy:
            policies.append(sector_policy)
            logger.info(f"Loaded sector policy: {sector}")
        else:
            logger.warning(f"No policy found for sector: {sector}")
        
        # Load regional policy if specified
        if region:
            regional_policy = self._load_regional_policy(region)
            if regional_policy:
                policies.append(regional_policy)
                logger.info(f"Loaded regional policy: {region}")
        
        # Load org-level policy if specified
        if org_level:
            org_policy = self._load_org_policy(org_level)
            if org_policy:
                policies.append(org_policy)
                logger.info(f"Loaded org-level policy: {org_level}")
        
        return policies
    
    def _load_sector_policy(self, sector: str) -> Optional[PolicyJSON]:
        """Load sector-specific policy. Maps Fintech -> BFSI if fintech.json not found."""
        sector_lower = sector.lower()
        sector_file = self.policies_base_path / "sectors" / f"{sector_lower}.json"
        policy = self._load_policy_file(sector_file)
        if policy is None and sector_lower == "fintech":
            # Use BFSI policy for Fintech (same regulatory family)
            sector_file = self.policies_base_path / "sectors" / "bfsi.json"
            policy = self._load_policy_file(sector_file)
            if policy:
                logger.info("Loaded BFSI policy for sector: Fintech")
        return policy
    
    def _load_regional_policy(self, region: str) -> Optional[PolicyJSON]:
        """Load region-specific policy"""
        region_file = self.policies_base_path / "regional" / f"{region.lower()}.json"
        return self._load_policy_file(region_file)
    
    def _load_org_policy(self, org_level: str) -> Optional[PolicyJSON]:
        """Load organization-level policy"""
        org_file = self.policies_base_path / "org" / f"{org_level.lower()}.json"
        return self._load_policy_file(org_file)
    
    def _load_policy_file(self, file_path: Path) -> Optional[PolicyJSON]:
        """Load and parse a policy JSON file"""
        try:
            if not file_path.exists():
                logger.debug(f"Policy file not found: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            policy = PolicyJSON(**data)
            logger.debug(f"Successfully loaded policy from {file_path}")
            return policy
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in policy file {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading policy file {file_path}: {e}")
            return None
