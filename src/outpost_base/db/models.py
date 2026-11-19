"""Database tables, matching the ER diagram in the docs repo."""

from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Node(SQLModel, table=True):
    __tablename__ = "nodes"

    node_id: int = Field(primary_key=True)
    name: str | None = None
    location: str | None = None
    protocol_version: int | None = None
    installed_at: datetime | None = None
    last_packet_at: datetime | None = None
    last_status_flags: int | None = None
    last_sequence: int | None = None


class Reading(SQLModel, table=True):
    __tablename__ = "readings"

    reading_id: int | None = Field(default=None, primary_key=True)
    node_id: int = Field(foreign_key="nodes.node_id", index=True)
    sequence: int
    node_timestamp: int | None = None
    received_at: datetime = Field(index=True)
    measured_at: datetime | None = None
    temperature_c: float | None = None
    humidity_pct: float | None = None
    pressure_pa: int | None = None
    wind_speed_ms: float | None = None
    wind_direction_deg: float | None = None
    battery_mv: int | None = None
    status_flags: int = 0
    faults: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    rssi_dbm: float | None = None
    snr_db: float | None = None
    protocol_version: int
    raw_payload: bytes | None = None


class Report(SQLModel, table=True):
    __tablename__ = "reports"

    report_id: int | None = Field(default=None, primary_key=True)
    node_id: int = Field(foreign_key="nodes.node_id", index=True)
    report_date: str  # local date the report covers, YYYY-MM-DD
    created_at: datetime
    generation_method: str  # cloud, local, or template
    model: str | None = None
    report_json: dict = Field(sa_column=Column(JSON))
    validation_passed: bool = False
    failed_claims: list | None = Field(default=None, sa_column=Column(JSON))
    attempts: int = 1
    failure_reason: str | None = None


class ReportInput(SQLModel, table=True):
    __tablename__ = "report_inputs"

    report_id: int = Field(foreign_key="reports.report_id", primary_key=True)
    stats_json: dict = Field(sa_column=Column(JSON))
    schema_version: str
    window_start: datetime
    window_end: datetime
