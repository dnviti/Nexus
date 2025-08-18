"""
Security Center Plugin

A comprehensive security plugin providing authentication, authorization,
audit logging, and security monitoring with web API and UI.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, IPvAnyAddress

from nexus.plugins import BasePlugin

logger = logging.getLogger(__name__)


# Data Models
class SecurityEvent(BaseModel):
    """Security event model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str  # login_attempt, permission_denied, suspicious_activity, etc.
    severity: str = "medium"  # low, medium, high, critical
    user_id: Optional[str] = None
    username: Optional[str] = None
    ip_address: str = ""
    user_agent: str = ""
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None


class AuditLog(BaseModel):
    """Audit log model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    username: str
    action: str
    resource: str
    resource_id: Optional[str] = None
    old_values: Dict[str, Any] = Field(default_factory=dict)
    new_values: Dict[str, Any] = Field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""
    success: bool = True
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SecurityRule(BaseModel):
    """Security rule model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    rule_type: str  # rate_limit, geo_block, pattern_match, etc.
    conditions: Dict[str, Any] = Field(default_factory=dict)
    actions: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    triggered_count: int = 0
    last_triggered: Optional[datetime] = None


class ThreatIntelligence(BaseModel):
    """Threat intelligence model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    threat_type: str  # malicious_ip, known_attack_pattern, etc.
    value: str  # IP address, pattern, hash, etc.
    source: str = "internal"
    confidence: float = 0.5  # 0.0 to 1.0
    description: str = ""
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


class SecurityAlert(BaseModel):
    """Security alert model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str
    severity: str = "medium"  # low, medium, high, critical
    category: str = "general"
    affected_resources: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    status: str = "open"  # open, investigating, resolved, false_positive
    assigned_to: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SecurityCenterPlugin(BasePlugin):
    """Security Center Plugin with comprehensive security monitoring."""

    def __init__(self):
        super().__init__()
        self.name = "security_center"
        self.version = "1.0.0"
        self.category = "security"
        self.description = "Comprehensive security monitoring and management system"

        # Storage
        self.security_events: List[SecurityEvent] = []
        self.audit_logs: List[AuditLog] = []
        self.security_rules: List[SecurityRule] = []
        self.threat_intelligence: List[ThreatIntelligence] = []
        self.security_alerts: List[SecurityAlert] = []

        # Tracking data
        self.failed_login_attempts: Dict[str, List[datetime]] = {}
        self.blocked_ips: Dict[str, datetime] = {}

        # Initialize with sample data
        self._initialize_sample_data()

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        logger.info(f"Initializing {self.name} plugin v{self.version}")

        # Create database schema
        await self._create_database_schema()

        # Load default security rules
        await self._load_default_rules()

        # Start security monitoring
        await self._start_security_monitoring()

        # Subscribe to security-related events
        await self._subscribe_to_events()

        logger.info(f"{self.name} plugin initialized successfully")
        return True

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        logger.info(f"Shutting down {self.name} plugin")
        await self.publish_event(
            "security_center.shutdown",
            {"plugin": self.name, "timestamp": datetime.utcnow().isoformat()},
        )

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for this plugin."""
        router = APIRouter(prefix="/plugins/security_center", tags=["security"])

        # Security Events endpoints
        @router.get("/events")
        async def get_security_events(
            severity: Optional[str] = None,
            event_type: Optional[str] = None,
            resolved: Optional[bool] = None,
            limit: int = 100,
            offset: int = 0,
        ):
            """Get security events with filtering."""
            filtered_events = self.security_events

            if severity:
                filtered_events = [e for e in filtered_events if e.severity == severity]
            if event_type:
                filtered_events = [e for e in filtered_events if e.event_type == event_type]
            if resolved is not None:
                filtered_events = [e for e in filtered_events if e.resolved == resolved]

            # Sort by timestamp (newest first)
            filtered_events = sorted(filtered_events, key=lambda x: x.timestamp, reverse=True)

            total = len(filtered_events)
            events = filtered_events[offset : offset + limit]

            return {
                "events": [event.dict() for event in events],
                "total": total,
                "limit": limit,
                "offset": offset,
            }

        @router.post("/events")
        async def create_security_event(event_data: SecurityEvent, request: Request):
            """Create a new security event."""
            # Set request metadata if not provided
            if not event_data.ip_address:
                event_data.ip_address = self._get_client_ip(request)
            if not event_data.user_agent:
                event_data.user_agent = request.headers.get("user-agent", "")

            self.security_events.append(event_data)

            # Check if event triggers security rules
            await self._check_security_rules(event_data)

            await self.publish_event(
                "security_center.event.created",
                {
                    "event_id": event_data.id,
                    "event_type": event_data.event_type,
                    "severity": event_data.severity,
                },
            )

            return {"message": "Security event created", "event_id": event_data.id}

        @router.put("/events/{event_id}/resolve")
        async def resolve_security_event(event_id: str, resolved_by: str):
            """Resolve a security event."""
            event = next((e for e in self.security_events if e.id == event_id), None)
            if not event:
                raise HTTPException(status_code=404, detail="Security event not found")

            event.resolved = True
            event.resolved_by = resolved_by
            event.resolved_at = datetime.utcnow()

            return {"message": "Security event resolved"}

        # Audit Logs endpoints
        @router.get("/audit-logs")
        async def get_audit_logs(
            user_id: Optional[str] = None,
            action: Optional[str] = None,
            resource: Optional[str] = None,
            success: Optional[bool] = None,
            limit: int = 100,
            offset: int = 0,
        ):
            """Get audit logs with filtering."""
            filtered_logs = self.audit_logs

            if user_id:
                filtered_logs = [log for log in filtered_logs if log.user_id == user_id]
            if action:
                filtered_logs = [log for log in filtered_logs if log.action == action]
            if resource:
                filtered_logs = [log for log in filtered_logs if log.resource == resource]
            if success is not None:
                filtered_logs = [log for log in filtered_logs if log.success == success]

            # Sort by timestamp (newest first)
            filtered_logs = sorted(filtered_logs, key=lambda x: x.timestamp, reverse=True)

            total = len(filtered_logs)
            logs = filtered_logs[offset : offset + limit]

            return {
                "logs": [log.dict() for log in logs],
                "total": total,
                "limit": limit,
                "offset": offset,
            }

        @router.post("/audit-logs")
        async def create_audit_log(log_data: AuditLog, request: Request):
            """Create a new audit log entry."""
            # Set request metadata if not provided
            if not log_data.ip_address:
                log_data.ip_address = self._get_client_ip(request)
            if not log_data.user_agent:
                log_data.user_agent = request.headers.get("user-agent", "")

            self.audit_logs.append(log_data)

            return {"message": "Audit log created", "log_id": log_data.id}

        # Security Rules endpoints
        @router.get("/rules")
        async def get_security_rules():
            """Get all security rules."""
            return {"rules": [rule.dict() for rule in self.security_rules]}

        @router.post("/rules")
        async def create_security_rule(rule_data: SecurityRule):
            """Create a new security rule."""
            self.security_rules.append(rule_data)

            await self.publish_event(
                "security_center.rule.created",
                {"rule_id": rule_data.id, "rule_name": rule_data.name},
            )

            return {"message": "Security rule created", "rule_id": rule_data.id}

        @router.put("/rules/{rule_id}")
        async def update_security_rule(rule_id: str, rule_data: SecurityRule):
            """Update a security rule."""
            rule = next((r for r in self.security_rules if r.id == rule_id), None)
            if not rule:
                raise HTTPException(status_code=404, detail="Security rule not found")

            rule_data.id = rule_id
            rule_data.created_at = rule.created_at
            rule_data.triggered_count = rule.triggered_count
            rule_data.last_triggered = rule.last_triggered

            self.security_rules = [r if r.id != rule_id else rule_data for r in self.security_rules]

            return {"message": "Security rule updated"}

        @router.delete("/rules/{rule_id}")
        async def delete_security_rule(rule_id: str):
            """Delete a security rule."""
            original_count = len(self.security_rules)
            self.security_rules = [r for r in self.security_rules if r.id != rule_id]

            if len(self.security_rules) == original_count:
                raise HTTPException(status_code=404, detail="Security rule not found")

            return {"message": "Security rule deleted"}

        # Threat Intelligence endpoints
        @router.get("/threats")
        async def get_threat_intelligence():
            """Get threat intelligence data."""
            return {"threats": [threat.dict() for threat in self.threat_intelligence]}

        @router.post("/threats")
        async def add_threat_intelligence(threat_data: ThreatIntelligence):
            """Add threat intelligence data."""
            self.threat_intelligence.append(threat_data)

            return {"message": "Threat intelligence added", "threat_id": threat_data.id}

        # Security Alerts endpoints
        @router.get("/alerts")
        async def get_security_alerts(
            severity: Optional[str] = None,
            status: Optional[str] = None,
            limit: int = 100,
            offset: int = 0,
        ):
            """Get security alerts."""
            filtered_alerts = self.security_alerts

            if severity:
                filtered_alerts = [a for a in filtered_alerts if a.severity == severity]
            if status:
                filtered_alerts = [a for a in filtered_alerts if a.status == status]

            # Sort by created_at (newest first)
            filtered_alerts = sorted(filtered_alerts, key=lambda x: x.created_at, reverse=True)

            total = len(filtered_alerts)
            alerts = filtered_alerts[offset : offset + limit]

            return {
                "alerts": [alert.dict() for alert in alerts],
                "total": total,
                "limit": limit,
                "offset": offset,
            }

        @router.put("/alerts/{alert_id}/status")
        async def update_alert_status(
            alert_id: str, status: str, assigned_to: Optional[str] = None
        ):
            """Update security alert status."""
            alert = next((a for a in self.security_alerts if a.id == alert_id), None)
            if not alert:
                raise HTTPException(status_code=404, detail="Security alert not found")

            alert.status = status
            alert.updated_at = datetime.utcnow()
            if assigned_to:
                alert.assigned_to = assigned_to

            return {"message": "Alert status updated"}

        # Analytics endpoints
        @router.get("/analytics/overview")
        async def get_security_overview():
            """Get security analytics overview."""
            now = datetime.utcnow()
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)

            # Security events stats
            recent_events = [e for e in self.security_events if e.timestamp >= last_24h]
            weekly_events = [e for e in self.security_events if e.timestamp >= last_7d]

            critical_events = [e for e in recent_events if e.severity == "critical"]
            high_events = [e for e in recent_events if e.severity == "high"]

            # Alerts stats
            open_alerts = [a for a in self.security_alerts if a.status == "open"]
            critical_alerts = [a for a in open_alerts if a.severity == "critical"]

            # Event types distribution
            event_types = {}
            for event in recent_events:
                event_types[event.event_type] = event_types.get(event.event_type, 0) + 1

            # Top threat sources (IPs)
            threat_sources = {}
            for event in recent_events:
                if event.ip_address:
                    threat_sources[event.ip_address] = threat_sources.get(event.ip_address, 0) + 1

            top_threats = sorted(threat_sources.items(), key=lambda x: x[1], reverse=True)[:5]

            return {
                "total_events": len(self.security_events),
                "events_24h": len(recent_events),
                "events_7d": len(weekly_events),
                "critical_events_24h": len(critical_events),
                "high_events_24h": len(high_events),
                "open_alerts": len(open_alerts),
                "critical_alerts": len(critical_alerts),
                "active_rules": len([r for r in self.security_rules if r.is_active]),
                "threat_intelligence_entries": len(self.threat_intelligence),
                "event_types": event_types,
                "top_threat_sources": top_threats,
            }

        # Security Actions endpoints
        @router.post("/actions/block-ip")
        async def block_ip_address(ip_address: str, duration_hours: int = 24, reason: str = ""):
            """Block an IP address."""
            expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
            self.blocked_ips[ip_address] = expires_at

            # Create security event
            event = SecurityEvent(
                event_type="ip_blocked",
                severity="medium",
                ip_address=ip_address,
                description=f"IP address {ip_address} blocked for {duration_hours} hours. Reason: {reason}",
                metadata={
                    "duration_hours": duration_hours,
                    "reason": reason,
                    "expires_at": expires_at.isoformat(),
                },
            )
            self.security_events.append(event)

            await self.publish_event(
                "security_center.ip.blocked",
                {"ip_address": ip_address, "duration_hours": duration_hours, "reason": reason},
            )

            return {
                "message": f"IP {ip_address} blocked successfully",
                "expires_at": expires_at.isoformat(),
            }

        @router.delete("/actions/unblock-ip/{ip_address}")
        async def unblock_ip_address(ip_address: str):
            """Unblock an IP address."""
            if ip_address in self.blocked_ips:
                del self.blocked_ips[ip_address]

                # Create security event
                event = SecurityEvent(
                    event_type="ip_unblocked",
                    severity="low",
                    ip_address=ip_address,
                    description=f"IP address {ip_address} unblocked",
                )
                self.security_events.append(event)

                return {"message": f"IP {ip_address} unblocked successfully"}
            else:
                raise HTTPException(status_code=404, detail="IP address not found in blocked list")

        @router.get("/actions/blocked-ips")
        async def get_blocked_ips():
            """Get list of blocked IP addresses."""
            now = datetime.utcnow()
            active_blocks = {
                ip: expires for ip, expires in self.blocked_ips.items() if expires > now
            }

            # Clean up expired blocks
            self.blocked_ips = active_blocks

            return {
                "blocked_ips": {ip: expires.isoformat() for ip, expires in active_blocks.items()}
            }

        # Web UI
        @router.get("/ui", response_class=HTMLResponse)
        async def security_center_ui():
            """Serve the security center management UI."""
            return self._get_security_center_html()

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for this plugin."""
        return {
            "collections": {
                f"{self.name}_events": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "event_type"},
                        {"field": "severity"},
                        {"field": "user_id"},
                        {"field": "timestamp"},
                        {"field": "resolved"},
                    ]
                },
                f"{self.name}_audit_logs": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "user_id"},
                        {"field": "action"},
                        {"field": "resource"},
                        {"field": "timestamp"},
                        {"field": "success"},
                    ]
                },
                f"{self.name}_rules": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "name"},
                        {"field": "rule_type"},
                        {"field": "is_active"},
                    ]
                },
                f"{self.name}_threats": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "threat_type"},
                        {"field": "value"},
                        {"field": "is_active"},
                    ]
                },
                f"{self.name}_alerts": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "severity"},
                        {"field": "status"},
                        {"field": "created_at"},
                    ]
                },
            }
        }

    # Helper methods
    def _initialize_sample_data(self):
        """Initialize with sample data."""
        # Sample security rules
        self.security_rules = [
            SecurityRule(
                name="Failed Login Rate Limit",
                description="Detect multiple failed login attempts from same IP",
                rule_type="rate_limit",
                conditions={"event_type": "login_failed", "count": 5, "window_minutes": 10},
                actions={"block_ip": True, "alert": True, "severity": "high"},
            ),
            SecurityRule(
                name="Admin Action Monitor",
                description="Monitor administrative actions",
                rule_type="pattern_match",
                conditions={"action": "admin_*", "resource": "*"},
                actions={"alert": True, "severity": "medium", "notify_admin": True},
            ),
            SecurityRule(
                name="Suspicious File Access",
                description="Detect access to sensitive files",
                rule_type="pattern_match",
                conditions={"resource": "/etc/passwd,/etc/shadow,config.json"},
                actions={"alert": True, "severity": "critical", "block_user": True},
            ),
        ]

        # Sample threat intelligence
        self.threat_intelligence = [
            ThreatIntelligence(
                threat_type="malicious_ip",
                value="192.168.1.100",
                source="internal_detection",
                confidence=0.8,
                description="IP address showing suspicious scanning behavior",
            ),
            ThreatIntelligence(
                threat_type="known_attack_pattern",
                value="sql_injection",
                source="threat_feed",
                confidence=0.9,
                description="Common SQL injection patterns",
            ),
        ]

        # Sample security events
        now = datetime.utcnow()
        self.security_events = [
            SecurityEvent(
                event_type="login_failed",
                severity="medium",
                ip_address="192.168.1.100",
                description="Failed login attempt for user 'admin'",
                metadata={"username": "admin", "attempts": 3},
                timestamp=now - timedelta(minutes=30),
            ),
            SecurityEvent(
                event_type="permission_denied",
                severity="high",
                user_id="user123",
                username="testuser",
                ip_address="192.168.1.50",
                description="Unauthorized access attempt to admin panel",
                timestamp=now - timedelta(hours=2),
            ),
            SecurityEvent(
                event_type="suspicious_activity",
                severity="critical",
                ip_address="10.0.0.200",
                description="Multiple failed authentication attempts from unknown IP",
                metadata={"attempts": 15, "timespan": "5 minutes"},
                timestamp=now - timedelta(hours=1),
            ),
        ]

        # Sample security alerts
        self.security_alerts = [
            SecurityAlert(
                title="Multiple Failed Login Attempts",
                description="IP address 192.168.1.100 has made 5 failed login attempts in the last 10 minutes",
                severity="high",
                category="authentication",
                affected_resources=["user_management"],
                recommendations=[
                    "Block IP address temporarily",
                    "Review user accounts for compromise",
                    "Check authentication logs",
                ],
                status="open",
            ),
            SecurityAlert(
                title="Suspicious File Access Pattern",
                description="Unusual access pattern detected for sensitive configuration files",
                severity="critical",
                category="data_access",
                affected_resources=["config_files", "user_data"],
                recommendations=[
                    "Review file access logs",
                    "Check user permissions",
                    "Consider implementing additional access controls",
                ],
                status="investigating",
            ),
        ]

    async def _create_database_schema(self):
        """Create database schema."""
        if self.db_adapter:
            schema = self.get_database_schema()
            logger.info(f"Database schema defined: {list(schema['collections'].keys())}")

    async def _load_default_rules(self):
        """Load default security rules."""
        logger.info(f"Loaded {len(self.security_rules)} default security rules")

    async def _start_security_monitoring(self):
        """Start security monitoring tasks."""
        await self.publish_event(
            "security_center.monitoring.started",
            {"plugin": self.name, "rules_count": len(self.security_rules)},
        )

    async def _subscribe_to_events(self):
        """Subscribe to security-related events."""
        # In a real implementation, this would subscribe to various system events
        logger.info("Subscribed to security-related events")

    async def _check_security_rules(self, event: SecurityEvent):
        """Check if security event triggers any rules."""
        for rule in self.security_rules:
            if not rule.is_active:
                continue

            if await self._rule_matches_event(rule, event):
                rule.triggered_count += 1
                rule.last_triggered = datetime.utcnow()

                # Execute rule actions
                await self._execute_rule_actions(rule, event)

    async def _rule_matches_event(self, rule: SecurityRule, event: SecurityEvent) -> bool:
        """Check if a rule matches an event."""
        conditions = rule.conditions

        # Simple pattern matching for demonstration
        if rule.rule_type == "pattern_match":
            if "event_type" in conditions and conditions["event_type"] != event.event_type:
                return False

        elif rule.rule_type == "rate_limit":
            if "event_type" in conditions:
                if conditions["event_type"] != event.event_type:
                    return False

                # Check rate limit
                window_minutes = conditions.get("window_minutes", 10)
                count_threshold = conditions.get("count", 5)

                cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
                recent_events = [
                    e
                    for e in self.security_events
                    if e.event_type == event.event_type
                    and e.ip_address == event.ip_address
                    and e.timestamp >= cutoff_time
                ]

                return len(recent_events) >= count_threshold

        return False

    async def _execute_rule_actions(self, rule: SecurityRule, event: SecurityEvent):
        """Execute actions defined by a security rule."""
        actions = rule.actions

        if actions.get("block_ip") and event.ip_address:
            duration_hours = actions.get("block_duration_hours", 1)
            expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
            self.blocked_ips[event.ip_address] = expires_at

        if actions.get("alert"):
            alert = SecurityAlert(
                title=f"Security Rule Triggered: {rule.name}",
                description=f"Rule '{rule.name}' was triggered by event: {event.description}",
                severity=actions.get("severity", "medium"),
                category="rule_triggered",
                affected_resources=[event.event_type],
                recommendations=["Review security event details", "Investigate potential threat"],
            )
            self.security_alerts.append(alert)

        # Publish event about rule trigger
        await self.publish_event(
            "security_center.rule.triggered",
            {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "event_id": event.id,
                "severity": actions.get("severity", "medium"),
            },
        )

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0]
        return request.client.host if request.client else "unknown"

    def _get_security_center_html(self) -> str:
        """Generate the security center HTML UI."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Center - Nexus Platform</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
        }

        .header {
            background: #1e293b;
            padding: 1rem 2rem;
            border-bottom: 1px solid #334155;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        }

        .header h1 {
            color: #ef4444;
            font-size: 1.5rem;
            font-weight: 600;
        }

        .nav {
            display: flex;
            gap: 2rem;
            margin-top: 1rem;
        }

        .nav-item {
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            transition: background-color 0.2s;
            color: #94a3b8;
        }

        .nav-item:hover {
            background: #334155;
            color: #e2e8f0;
        }

        .nav-item.active {
            background: #ef4444;
            color: white;
        }

        .container {
            max-width: 1400px;
            margin: 2rem auto;
            padding: 0 1rem;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: #1e293b;
            padding: 1.5rem;
            border-radius: 8px;
            border: 1px solid #334155;
            text-align: center;
        }

        .stat-card.critical {
            border-color: #ef4444;
            background: linear-gradient(135deg, #1e293b 0%, #2d1b1b 100%);
        }

        .stat-card.warning {
            border-color: #f59e0b;
            background: linear-gradient(135deg, #1e293b 0%, #2d2518 100%);
        }

        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }

        .stat-value.critical { color: #ef4444; }
        .stat-value.warning { color: #f59e0b; }
        .stat-value.success { color: #10b981; }
        .stat-value.info { color: #3b82f6; }

        .stat-label {
            color: #94a3b8;
            font-size: 0.9rem;
        }

        .content-section {
            background: #1e293b;
            border-radius: 8px;
            border: 1px solid #334155;
            margin-bottom: 2rem;
        }

        .section-header {
            padding: 1.5rem;
            border-bottom: 1px solid #334155;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .section-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: #f1f5f9;
        }

        .section-content {
            padding: 1.5rem;
        }

        .alert-item {
            display: flex;
            align-items: center;
            padding: 1rem;
            border: 1px solid #334155;
            border-radius: 6px;
            margin-bottom: 1rem;
            transition: background-color 0.2s;
        }

        .alert-item:hover {
            background-color: #334155;
        }

        .alert-item.critical {
            border-color: #ef4444;
            background: linear-gradient(90deg, rgba(239, 68, 68, 0.1) 0%, transparent 100%);
        }

        .alert-item.high {
            border-color: #f59e0b;
            background: linear-gradient(90deg, rgba(245, 158, 11, 0.1) 0%, transparent 100%);
        }

        .alert-severity {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 1rem;
        }

        .severity-critical { background: #ef4444; }
        .severity-high { background: #f59e0b; }
        .severity-medium { background: #3b82f6; }
        .severity-low { background: #10b981; }

        .alert-info {
            flex: 1;
        }

        .alert-title {
            font-weight: 600;
            color: #f1f5f9;
            margin-bottom: 0.25rem;
        }

        .alert-description {
            color: #94a3b8;
            font-size: 0.9rem;
        }

        .alert-status {
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
        }

        .status-open { background: #fee2e2; color: #dc2626; }
        .status-investigating { background: #fef3c7; color: #d97706; }
        .status-resolved { background: #dcfce7; color: #16a34a; }

        .event-list {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .event-item {
            display: flex;
            align-items: center;
            padding: 0.75rem;
            border: 1px solid #334155;
            border-radius: 6px;
            transition: background-color 0.2s;
        }

        .event-item:hover {
            background-color: #334155;
        }

        .event-type {
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
            margin-right: 1rem;
        }

        .event-login { background: #1e40af; color: #dbeafe; }
        .event-permission { background: #dc2626; color: #fee2e2; }
        .event-suspicious { background: #7c2d12; color: #fed7aa; }

        .event-info {
            flex: 1;
        }

        .event-description {
            color: #e2e8f0;
            margin-bottom: 0.25rem;
        }

        .event-meta {
            color: #64748b;
            font-size: 0.8rem;
        }

        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 1rem;
        }

        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.2s;
        }

        .btn-danger {
            background: #ef4444;
            color: white;
        }

        .btn-danger:hover {
            background: #dc2626;
        }

        .btn-warning {
            background: #f59e0b;
            color: white;
        }

        .btn-warning:hover {
            background: #d97706;
        }

        .btn-primary {
            background: #3b82f6;
            color: white;
        }

        .btn-primary:hover {
            background: #2563eb;
        }

        .loading {
            text-align: center;
            padding: 2rem;
            color: #64748b;
        }

        .hidden {
            display: none;
        }

        .threat-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 0.5rem;
        }

        .threat-high { background: #ef4444; }
        .threat-medium { background: #f59e0b; }
        .threat-low { background: #10b981; }

        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }

            .alert-item,
            .event-item {
                flex-direction: column;
                align-items: flex-start;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ Security Center</h1>
        <div class="nav">
            <div class="nav-item active" onclick="showSection('overview')">Overview</div>
            <div class="nav-item" onclick="showSection('alerts')">Security Alerts</div>
            <div class="nav-item" onclick="showSection('events')">Security Events</div>
            <div class="nav-item" onclick="showSection('threats')">Threat Intelligence</div>
        </div>
    </div>

    <div class="container">
        <!-- Overview Section -->
        <div id="overview" class="section">
            <div class="stats-grid">
                <div class="stat-card critical">
                    <div class="stat-value critical" id="criticalEvents">-</div>
                    <div class="stat-label">Critical Events (24h)</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-value warning" id="highEvents">-</div>
                    <div class="stat-label">High Severity Events (24h)</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value info" id="openAlerts">-</div>
                    <div class="stat-label">Open Alerts</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value success" id="activeRules">-</div>
                    <div class="stat-label">Active Security Rules</div>
                </div>
            </div>

            <div class="content-section">
                <div class="section-header">
                    <div class="section-title">Security Status Dashboard</div>
                    <button class="btn btn-primary" onclick="refreshDashboard()">🔄 Refresh</button>
                </div>
                <div class="section-content">
                    <div class="chart-container">
                        <canvas id="threatChart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Alerts Section -->
        <div id="alerts" class="section hidden">
            <div class="content-section">
                <div class="section-header">
                    <div class="section-title">Security Alerts</div>
                    <button class="btn btn-primary" onclick="loadAlerts()">🔄 Refresh</button>
                </div>
                <div class="section-content">
                    <div id="alertsList" class="loading">Loading alerts...</div>
                </div>
            </div>
        </div>

        <!-- Events Section -->
        <div id="events" class="section hidden">
            <div class="content-section">
                <div class="section-header">
                    <div class="section-title">Security Events</div>
                    <button class="btn btn-primary" onclick="loadEvents()">🔄 Refresh</button>
                </div>
                <div class="section-content">
                    <div id="eventsList" class="loading">Loading events...</div>
                </div>
            </div>
        </div>

        <!-- Threats Section -->
        <div id="threats" class="section hidden">
            <div class="content-section">
                <div class="section-header">
                    <div class="section-title">Threat Intelligence</div>
                    <button class="btn btn-primary" onclick="loadThreats()">🔄 Refresh</button>
                </div>
                <div class="section-content">
                    <div id="threatsList" class="loading">Loading threat intelligence...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let threatChart;

        async function loadDashboard() {
            try {
                const response = await fetch('/plugins/security_center/analytics/overview');
                const data = await response.json();

                // Update stats
                document.getElementById('criticalEvents').textContent = data.critical_events_24h;
                document.getElementById('highEvents').textContent = data.high_events_24h;
                document.getElementById('openAlerts').textContent = data.open_alerts;
                document.getElementById('activeRules').textContent = data.active_rules;

                // Load threat chart
                loadThreatChart(data);

            } catch (error) {
                console.error('Error loading dashboard:', error);
            }
        }

        function loadThreatChart(data) {
            const ctx = document.getElementById('threatChart').getContext('2d');

            if (threatChart) {
                threatChart.destroy();
            }

            // Create chart from event types
            const eventTypes = data.event_types || {};
            const labels = Object.keys(eventTypes);
            const values = Object.values(eventTypes);

            threatChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels.map(type => type.replace('_', ' ').toUpperCase()),
                    datasets: [{
                        label: 'Events (Last 24h)',
                        data: values,
                        backgroundColor: [
                            '#ef4444', '#f59e0b', '#3b82f6', '#10b981', '#8b5cf6'
                        ],
                        borderColor: '#334155',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        title: {
                            display: true,
                            text: 'Security Events by Type (Last 24h)',
                            color: '#e2e8f0'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { color: '#94a3b8' },
                            grid: { color: '#334155' }
                        },
                        x: {
                            ticks: { color: '#94a3b8' },
                            grid: { color: '#334155' }
                        }
                    }
                }
            });
        }

        async function loadAlerts() {
            try {
                const response = await fetch('/plugins/security_center/alerts');
                const data = await response.json();
                displayAlerts(data.alerts);
            } catch (error) {
                console.error('Error loading alerts:', error);
                document.getElementById('alertsList').innerHTML = '<div class="loading">Error loading alerts</div>';
            }
        }

        function displayAlerts(alerts) {
            const container = document.getElementById('alertsList');

            if (!alerts || alerts.length === 0) {
                container.innerHTML = '<div class="loading">No security alerts found</div>';
                return;
            }

            container.innerHTML = alerts.map(alert => `
                <div class="alert-item ${alert.severity}">
                    <div class="alert-severity severity-${alert.severity}"></div>
                    <div class="alert-info">
                        <div class="alert-title">${alert.title}</div>
                        <div class="alert-description">${alert.description}</div>
                    </div>
                    <div>
                        <span class="alert-status status-${alert.status}">${alert.status.toUpperCase()}</span>
                    </div>
                </div>
            `).join('');
        }

        async function loadEvents() {
            try {
                const response = await fetch('/plugins/security_center/events?limit=20');
                const data = await response.json();
                displayEvents(data.events);
            } catch (error) {
                console.error('Error loading events:', error);
                document.getElementById('eventsList').innerHTML = '<div class="loading">Error loading events</div>';
            }
        }

        function displayEvents(events) {
            const container = document.getElementById('eventsList');

            if (!events || events.length === 0) {
                container.innerHTML = '<div class="loading">No security events found</div>';
                return;
            }

            container.innerHTML = events.map(event => `
                <div class="event-item">
                    <span class="event-type event-${event.event_type.split('_')[0]}">${event.event_type.replace('_', ' ').toUpperCase()}</span>
                    <div class="event-info">
                        <div class="event-description">${event.description}</div>
                        <div class="event-meta">
                            IP: ${event.ip_address || 'Unknown'} |
                            ${formatTime(event.timestamp)} |
                            Severity: ${event.severity.toUpperCase()}
                        </div>
                    </div>
                    <div class="threat-indicator threat-${event.severity}"></div>
                </div>
            `).join('');
        }

        async function loadThreats() {
            try {
                const response = await fetch('/plugins/security_center/threats');
                const data = await response.json();
                displayThreats(data.threats);
            } catch (error) {
                console.error('Error loading threats:', error);
                document.getElementById('threatsList').innerHTML = '<div class="loading">Error loading threats</div>';
            }
        }

        function displayThreats(threats) {
            const container = document.getElementById('threatsList');

            if (!threats || threats.length === 0) {
                container.innerHTML = '<div class="loading">No threat intelligence data found</div>';
                return;
            }

            container.innerHTML = threats.map(threat => {
                const confidenceLevel = threat.confidence > 0.7 ? 'high' : threat.confidence > 0.4 ? 'medium' : 'low';
                return `
                    <div class="event-item">
                        <span class="event-type event-${threat.threat_type.split('_')[0]}">${threat.threat_type.replace('_', ' ').toUpperCase()}</span>
                        <div class="event-info">
                            <div class="event-description">${threat.description}</div>
                            <div class="event-meta">
                                Value: ${threat.value} |
                                Source: ${threat.source} |
                                Confidence: ${Math.round(threat.confidence * 100)}%
                            </div>
                        </div>
                        <div class="threat-indicator threat-${confidenceLevel}"></div>
                    </div>
                `;
            }).join('');
        }

        function showSection(sectionName) {
            // Hide all sections
            document.querySelectorAll('.section').forEach(section => {
                section.classList.add('hidden');
            });

            // Remove active class from nav items
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });

            // Show selected section
            document.getElementById(sectionName).classList.remove('hidden');

            // Add active class to clicked nav item
            event.target.classList.add('active');

            // Load section-specific data
            if (sectionName === 'alerts') {
                loadAlerts();
            } else if (sectionName === 'events') {
                loadEvents();
            } else if (sectionName === 'threats') {
                loadThreats();
            }
        }

        function formatTime(timestamp) {
            return new Date(timestamp).toLocaleString();
        }

        function refreshDashboard() {
            loadDashboard();
        }

        // Load dashboard on page load
        document.addEventListener('DOMContentLoaded', loadDashboard);

        // Auto-refresh every 60 seconds
        setInterval(() => {
            if (!document.getElementById('overview').classList.contains('hidden')) {
                loadDashboard();
            }
        }, 60000);
    </script>
</body>
</html>
        """
