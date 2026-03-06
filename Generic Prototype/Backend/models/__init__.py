"""SQLAlchemy models for configurator. Import Base for create_all."""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from db.base import Base


class IntentSession(Base):
    __tablename__ = "intent_sessions"
    id = Column(String(36), primary_key=True)
    org_id = Column(String(64), nullable=False, index=True)
    project_id = Column(String(64), nullable=True, index=True)
    status = Column(String(32), default="IN_PROGRESS")
    current_question_id = Column(String(64), nullable=True)
    answers = Column(JSON, default=dict)
    inferred_intent = Column(JSON, default=dict)
    conversation_history = Column(JSON, default=list)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IntentSchema(Base):
    __tablename__ = "intent_schemas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(String(64), nullable=False, index=True)
    version = Column(String(32), nullable=False)
    is_active = Column(Boolean, default=True)
    schema_fields = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    def get_fields(self):
        return self.schema_fields or []


class IntentField(Base):
    __tablename__ = "intent_fields"
    id = Column(Integer, primary_key=True, autoincrement=True)
    schema_id = Column(Integer, ForeignKey("intent_schemas.id"), nullable=False)
    field_path = Column(String(128), nullable=False)
    section = Column(String(64), nullable=True)
    field_type = Column(String(32), default="string")
    required = Column(Boolean, default=False)
    description = Column(Text, nullable=True)


class Topology(Base):
    __tablename__ = "topologies"
    id = Column(String(36), primary_key=True)
    project_id = Column(String(64), nullable=False, index=True)
    org_id = Column(String(64), nullable=False, index=True)
    status = Column(String(32), default="COMPLETED")
    intent_snapshot = Column(JSON, default=dict)
    schema_version = Column(String(32), nullable=True)
    session_id = Column(String(36), ForeignKey("intent_sessions.id"), nullable=True)
    version = Column(Integer, default=1)
    layout_mode = Column(String(32), nullable=True)
    node_positions = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    nodes = relationship("TopologyNode", back_populates="topology", cascade="all, delete-orphan")
    edges = relationship("TopologyEdge", back_populates="topology", cascade="all, delete-orphan", foreign_keys="TopologyEdge.topology_id")


class TopologyNode(Base):
    __tablename__ = "topology_nodes"
    id = Column(String(64), primary_key=True)
    topology_id = Column(String(36), ForeignKey("topologies.id"), nullable=False)
    block_id = Column(String(64), nullable=False)
    instance_name = Column(String(128), nullable=True)
    layer = Column(Integer, default=2)
    region = Column(String(64), nullable=True)
    container_id = Column(String(64), nullable=True)
    spec = Column(JSON, default=dict)
    ha_role = Column(String(32), nullable=True)
    capability_ref = Column(String(64), nullable=True)
    category = Column(String(32), nullable=True)
    node_type = Column(String(32), nullable=True)
    data_label = Column(String(256), nullable=True)
    parent_node = Column(String(64), nullable=True)
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    topology = relationship("Topology", back_populates="nodes")


class TopologyEdge(Base):
    __tablename__ = "topology_edges"
    id = Column(String(64), primary_key=True)
    topology_id = Column(String(36), ForeignKey("topologies.id"), nullable=False)
    source_node_id = Column(String(64), nullable=False)
    target_node_id = Column(String(64), nullable=False)
    protocol = Column(String(32), nullable=True)
    edge_type = Column(String(32), nullable=True)
    topology = relationship("Topology", back_populates="edges")


class Block(Base):
    __tablename__ = "blocks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    block_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    category = Column(String(32), nullable=False)
    version = Column(String(32), default="1.0")
    capabilities = Column(JSON, default=dict)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompliancePolicy(Base):
    __tablename__ = "compliance_policies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(String(64), nullable=False, index=True)
    level = Column(String(32), nullable=True)
    version = Column(String(32), default="1.0")
    created_at = Column(DateTime, default=datetime.utcnow)
    constraint_rules = relationship("ConstraintRule", back_populates="policy", cascade="all, delete-orphan")


class ConstraintRule(Base):
    __tablename__ = "constraint_rules"
    id = Column(Integer, primary_key=True, autoincrement=True)
    policy_id = Column(Integer, ForeignKey("compliance_policies.id"), nullable=False)
    resource_type = Column(String(64), nullable=True)
    operation = Column(String(64), nullable=True)
    policy_field = Column(String(64), nullable=True)
    policy_value = Column(Text, nullable=True)
    policy = relationship("CompliancePolicy", back_populates="constraint_rules")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(128), nullable=True)
    action = Column(String(64), nullable=False)
    payload = Column(JSON, default=dict)
    status = Column(String(32), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
