# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Audit Service - Tracks configuration changes for compliance and debugging.

Provides audit trail functionality for model configuration changes
following ADCL principles with detailed change tracking.
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

from app.core.logging import get_service_logger

logger = get_service_logger("audit")


@dataclass
class AuditEntry:
    """Single audit trail entry"""
    timestamp: str
    action: str  # create, update, delete, set_default
    resource_type: str  # model, configuration
    resource_id: str
    user_id: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuditService:
    """
    Manages audit trail for configuration changes.
    
    Responsibilities:
    - Record configuration changes
    - Provide audit trail queries
    - Maintain audit log files
    - Support compliance reporting
    """
    
    def __init__(self, audit_log_path: Path):
        """
        Initialize AuditService.
        
        Args:
            audit_log_path: Path to audit log file
        """
        self.audit_log_path = audit_log_path
        self.lock = asyncio.Lock()
        
        # Ensure audit log directory exists
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"AuditService initialized with log: {audit_log_path}")
    
    async def record_change(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        changes: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEntry:
        """
        Record a configuration change in the audit trail.
        
        Args:
            action: Type of action (create, update, delete, set_default)
            resource_type: Type of resource (model, configuration)
            resource_id: Identifier of the resource
            changes: Dictionary of changes made (old_value -> new_value)
            reason: Reason for the change
            user_id: User who made the change
            metadata: Additional metadata
            
        Returns:
            Created audit entry
        """
        async with self.lock:
            entry = AuditEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
                changes=changes,
                reason=reason,
                metadata=metadata
            )
            
            # Append to audit log file
            try:
                with open(self.audit_log_path, "a", encoding='utf-8') as f:
                    f.write(json.dumps(entry.to_dict()) + "\n")
                
                logger.info(f"Recorded audit entry: {action} {resource_type} {resource_id}")
                return entry
                
            except Exception as e:
                logger.error(f"Failed to write audit entry: {e}")
                raise
    
    async def get_audit_trail(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[AuditEntry]:
        """
        Retrieve audit trail entries with optional filtering.
        
        Args:
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            action: Filter by action type
            limit: Maximum number of entries to return
            
        Returns:
            List of audit entries
        """
        async with self.lock:
            entries = []
            
            try:
                if not self.audit_log_path.exists():
                    return entries
                
                with open(self.audit_log_path, "r", encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                            
                        try:
                            entry_data = json.loads(line)
                            entry = AuditEntry(**entry_data)
                            
                            # Apply filters
                            if resource_type and entry.resource_type != resource_type:
                                continue
                            if resource_id and entry.resource_id != resource_id:
                                continue
                            if action and entry.action != action:
                                continue
                            
                            entries.append(entry)
                            
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"Invalid audit entry: {line} - {e}")
                            continue
                
                # Sort by timestamp (newest first)
                entries.sort(key=lambda x: x.timestamp, reverse=True)
                
                # Apply limit
                if limit:
                    entries = entries[:limit]
                
                return entries
                
            except Exception as e:
                logger.error(f"Failed to read audit trail: {e}")
                return []
    
    async def get_resource_history(self, resource_type: str, resource_id: str) -> List[AuditEntry]:
        """
        Get complete change history for a specific resource.
        
        Args:
            resource_type: Type of resource
            resource_id: Resource identifier
            
        Returns:
            List of audit entries for the resource
        """
        return await self.get_audit_trail(
            resource_type=resource_type,
            resource_id=resource_id
        )
    
    async def record_model_creation(
        self,
        model_id: str,
        model_data: Dict[str, Any],
        reason: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> AuditEntry:
        """
        Record model creation in audit trail.
        
        Args:
            model_id: Model identifier
            model_data: Complete model configuration
            reason: Reason for creation
            user_id: User who created the model
            
        Returns:
            Audit entry
        """
        return await self.record_change(
            action="create",
            resource_type="model",
            resource_id=model_id,
            changes={"created": model_data},
            reason=reason or "Model created",
            user_id=user_id,
            metadata={"provider": model_data.get("provider")}
        )
    
    async def record_model_update(
        self,
        model_id: str,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        reason: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> AuditEntry:
        """
        Record model update in audit trail.
        
        Args:
            model_id: Model identifier
            old_data: Previous model configuration
            new_data: Updated model configuration
            reason: Reason for update
            user_id: User who updated the model
            
        Returns:
            Audit entry
        """
        # Calculate specific changes
        changes = {}
        for key in set(old_data.keys()) | set(new_data.keys()):
            old_value = old_data.get(key)
            new_value = new_data.get(key)
            if old_value != new_value:
                changes[key] = {"old": old_value, "new": new_value}
        
        return await self.record_change(
            action="update",
            resource_type="model",
            resource_id=model_id,
            changes=changes,
            reason=reason or "Model updated",
            user_id=user_id,
            metadata={"provider": new_data.get("provider")}
        )
    
    async def record_model_deletion(
        self,
        model_id: str,
        model_data: Dict[str, Any],
        reason: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> AuditEntry:
        """
        Record model deletion in audit trail.
        
        Args:
            model_id: Model identifier
            model_data: Model configuration before deletion
            reason: Reason for deletion
            user_id: User who deleted the model
            
        Returns:
            Audit entry
        """
        return await self.record_change(
            action="delete",
            resource_type="model",
            resource_id=model_id,
            changes={"deleted": model_data},
            reason=reason or "Model deleted",
            user_id=user_id,
            metadata={"provider": model_data.get("provider")}
        )
    
    async def record_default_change(
        self,
        old_default_id: Optional[str],
        new_default_id: str,
        reason: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> AuditEntry:
        """
        Record default model change in audit trail.
        
        Args:
            old_default_id: Previous default model ID
            new_default_id: New default model ID
            reason: Reason for change
            user_id: User who changed the default
            
        Returns:
            Audit entry
        """
        changes = {
            "default_model": {
                "old": old_default_id,
                "new": new_default_id
            }
        }
        
        return await self.record_change(
            action="set_default",
            resource_type="model",
            resource_id=new_default_id,
            changes=changes,
            reason=reason or "Default model changed",
            user_id=user_id
        )
    
    async def record_edition_change(
        self,
        old_edition: Optional[str],
        new_edition: str,
        old_features: Optional[List[str]] = None,
        new_features: Optional[List[str]] = None,
        old_tools: Optional[List[str]] = None,
        new_tools: Optional[List[str]] = None,
        reason: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEntry:
        """
        Record edition change in audit trail for security compliance.
        
        Args:
            old_edition: Previous edition name
            new_edition: New edition name
            old_features: List of previously enabled features
            new_features: List of newly enabled features
            old_tools: List of previously available tools
            new_tools: List of newly available tools
            reason: Reason for edition change
            user_id: User who initiated the change
            metadata: Additional metadata (IP address, user agent, etc.)
            
        Returns:
            Audit entry
        """
        # Calculate feature and tool changes
        features_added = []
        features_removed = []
        tools_added = []
        tools_removed = []
        
        if old_features and new_features:
            old_feature_set = set(old_features)
            new_feature_set = set(new_features)
            features_added = list(new_feature_set - old_feature_set)
            features_removed = list(old_feature_set - new_feature_set)
        
        if old_tools and new_tools:
            old_tool_set = set(old_tools)
            new_tool_set = set(new_tools)
            tools_added = list(new_tool_set - old_tool_set)
            tools_removed = list(old_tool_set - new_tool_set)
        
        changes = {
            "edition": {
                "old": old_edition,
                "new": new_edition
            },
            "features": {
                "added": features_added,
                "removed": features_removed,
                "total_before": len(old_features) if old_features else 0,
                "total_after": len(new_features) if new_features else 0
            },
            "tools": {
                "added": tools_added,
                "removed": tools_removed,
                "total_before": len(old_tools) if old_tools else 0,
                "total_after": len(new_tools) if new_tools else 0
            }
        }
        
        # Include security-relevant metadata
        audit_metadata = {
            "edition_type": "security" if "red-team" in new_edition or "enterprise" in new_edition else "standard",
            "tool_access_change": len(tools_added) > 0 or len(tools_removed) > 0,
            "feature_access_change": len(features_added) > 0 or len(features_removed) > 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if metadata:
            audit_metadata.update(metadata)
        
        return await self.record_change(
            action="edition_change",
            resource_type="edition",
            resource_id=new_edition,
            changes=changes,
            reason=reason or f"Edition changed from {old_edition} to {new_edition}",
            user_id=user_id,
            metadata=audit_metadata
        )
    
    async def log_license_upgrade(
        self,
        old_license_type: str,
        new_license_type: str,
        organization: str,
        activated_features: Optional[List[str]] = None,
        deactivated_features: Optional[List[str]] = None,
        reason: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEntry:
        """
        Record license upgrade events for compliance and tracking.
        
        Args:
            old_license_type: Previous license type
            new_license_type: New license type
            organization: Organization name on the license
            activated_features: List of newly activated features
            deactivated_features: List of deactivated features
            reason: Reason for the upgrade
            user_id: User who initiated the upgrade
            metadata: Additional metadata
            
        Returns:
            Audit entry
        """
        changes = {
            "license_type": {
                "old": old_license_type,
                "new": new_license_type
            },
            "organization": organization,
            "features": {
                "activated": activated_features or [],
                "deactivated": deactivated_features or [],
                "net_change": len(activated_features or []) - len(deactivated_features or [])
            }
        }
        
        # Determine upgrade direction and impact
        license_hierarchy = ["community", "enterprise", "premium"]
        old_rank = license_hierarchy.index(old_license_type) if old_license_type in license_hierarchy else -1
        new_rank = license_hierarchy.index(new_license_type) if new_license_type in license_hierarchy else -1
        
        is_upgrade = new_rank > old_rank
        is_downgrade = new_rank < old_rank
        
        audit_metadata = {
            "upgrade_type": "upgrade" if is_upgrade else "downgrade" if is_downgrade else "lateral",
            "license_impact": "high" if is_upgrade and len(activated_features or []) > 0 else "medium",
            "feature_count_change": len(activated_features or []) - len(deactivated_features or []),
            "has_feature_activation": len(activated_features or []) > 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if metadata:
            audit_metadata.update(metadata)
        
        return await self.record_change(
            action="license_upgrade",
            resource_type="license",
            resource_id=f"{organization}:{new_license_type}",
            changes=changes,
            reason=reason or f"License upgraded from {old_license_type} to {new_license_type}",
            user_id=user_id,
            metadata=audit_metadata
        )

    async def record_tool_access_change(
        self,
        tool_name: str,
        action: str,  # granted, revoked, modified
        edition: str,
        previous_access: Optional[bool] = None,
        new_access: Optional[bool] = None,
        reason: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEntry:
        """
        Record tool access changes for security auditing.
        
        Args:
            tool_name: Name of the tool (e.g., "nmap_recon", "kali")
            action: Type of access change (granted, revoked, modified)
            edition: Current edition context
            previous_access: Previous access state
            new_access: New access state
            reason: Reason for access change
            user_id: User who initiated the change
            metadata: Additional security metadata
            
        Returns:
            Audit entry
        """
        changes = {
            "tool_access": {
                "tool": tool_name,
                "previous": previous_access,
                "current": new_access,
                "change_type": action
            },
            "edition_context": edition
        }
        
        audit_metadata = {
            "security_impact": "high" if tool_name in ["kali", "nmap_recon", "zap"] else "medium",
            "tool_category": "security" if tool_name in ["kali", "nmap_recon", "zap"] else "utility",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if metadata:
            audit_metadata.update(metadata)
        
        return await self.record_change(
            action=action,
            resource_type="tool_access",
            resource_id=tool_name,
            changes=changes,
            reason=reason or f"Tool access {action} for {tool_name}",
            user_id=user_id,
            metadata=audit_metadata
        )
    
    async def cleanup_old_entries(self, days_to_keep: int = 90) -> int:
        """
        Clean up old audit entries to manage log file size.
        
        Args:
            days_to_keep: Number of days of entries to keep
            
        Returns:
            Number of entries removed
        """
        async with self.lock:
            if not self.audit_log_path.exists():
                return 0
            
            cutoff_date = datetime.now(timezone.utc).timestamp() - (days_to_keep * 24 * 60 * 60)
            kept_entries = []
            removed_count = 0
            
            try:
                with open(self.audit_log_path, "r", encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        try:
                            entry_data = json.loads(line)
                            entry_timestamp = datetime.fromisoformat(entry_data["timestamp"]).timestamp()
                            
                            if entry_timestamp >= cutoff_date:
                                kept_entries.append(line)
                            else:
                                removed_count += 1
                                
                        except (json.JSONDecodeError, ValueError, KeyError):
                            # Keep invalid entries for manual review
                            kept_entries.append(line)
                
                # Rewrite file with kept entries
                with open(self.audit_log_path, "w", encoding='utf-8') as f:
                    for entry in kept_entries:
                        f.write(entry + "\n")
                
                logger.info(f"Cleaned up {removed_count} old audit entries")
                return removed_count
                
            except Exception as e:
                logger.error(f"Failed to cleanup audit entries: {e}")
                return 0


# Global singleton instance
_audit_service_instance: Optional['AuditService'] = None


def get_audit_service() -> AuditService:
    """
    Get the global AuditService instance.
    
    Returns:
        AuditService singleton instance
        
    Raises:
        RuntimeError: If AuditService not initialized
        
    Usage:
        from app.services.audit_service import get_audit_service
        
        audit_service = get_audit_service()
        await audit_service.record_change(...)
    """
    global _audit_service_instance
    
    if _audit_service_instance is None:
        raise RuntimeError(
            "AuditService not initialized. "
            "Call init_audit_service() in main.py startup"
        )
    
    return _audit_service_instance


def init_audit_service(audit_log_path: str = "logs/audit.jsonl") -> AuditService:
    """
    Initialize the global AuditService instance.
    
    Args:
        audit_log_path: Path to audit log file
        
    Returns:
        Initialized AuditService instance
        
    Note:
        This should be called once in main.py at application startup.
    """
    global _audit_service_instance
    from pathlib import Path
    
    _audit_service_instance = AuditService(Path(audit_log_path))
    logger.info(f"AuditService initialized: {audit_log_path}")
    
    return _audit_service_instance