"""Reusable read-only validation API; importing it performs no validation or stream changes.

The validate.py facade owns argument parsing and console output. Modules here
contain the single implementation of the existing validation and gate rules.
"""
from .common import (
    Invalid, require, shape, string, strings, digest_bytes, canonical, hash_value,
    unique_object, read_json, relative, path_text, local_file, digest_file,
    iso_date, timestamp, https, HEX,
)
from .snapshots import (git, file_metadata, snapshot, MANAGED, WALK_IGNORED)
from .approvals import (scope_fields, scope, approval)
from .state import (artifact, state, migrate_state, PHASES)
from .registry import registry, registry_file, registry_record, migrate_registry
from .package import package
from .inventory import inventory
from .runtime import (
    RuntimeInfo, AgentRun, detect_runtime, list_agents, list_models, resolve_model,
    agent_for_role, is_read_only_agent, dispatch, verify_session, independence_report,
)
from .intake import run_intake, save_brief, ProjectBrief, intake_cli
from .arch_team import decompose_brief, integrate_research, ArchitectureTeamPlan, arch_team_cli
from .research import execute_research, save_result, ResearchResult, research_cli
from .task_contracts import (
    TaskContract, CriticContract, LeadContract, LeadResult,
    create_implementation_contract, create_critic_contract, create_lead_contract,
    validate_contract, save_contract, load_contract, list_contracts, task_contracts_cli
)
from .project_view import build_project_view, save_project_view, project_view_cli
from .critic_report import (
    CriticReport, Reviewer, Coverage, Finding, parse_critic_report,
    validate_critic_report, report_prompt,
)
from .lead_execution import (
    run_department_lead, validate_lead_plan, parse_json_object, lead_execution_cli,
)
from .pair_execution import run_implementer, run_critic, repair_loop, pair_execution_cli
from .integration import collect_reviewed_tasks, run_integration_tests, generate_integration_report, save_integration_report, integration_cli

__all__ = [
    'Invalid', 'require', 'shape', 'string', 'strings', 'digest_bytes', 'canonical',
    'hash_value', 'unique_object', 'read_json', 'relative', 'path_text', 'local_file',
    'digest_file', 'iso_date', 'timestamp', 'https', 'HEX', 'git', 'file_metadata',
    'snapshot', 'MANAGED', 'WALK_IGNORED', 'scope_fields', 'scope', 'approval',
    'artifact', 'state', 'migrate_state', 'PHASES', 'registry', 'package',
    'registry_file', 'registry_record', 'migrate_registry',
    'inventory',
    'RuntimeInfo', 'AgentRun', 'detect_runtime', 'list_agents', 'list_models',
    'resolve_model', 'agent_for_role', 'is_read_only_agent', 'dispatch',
    'verify_session', 'independence_report',
    'run_intake', 'save_brief', 'ProjectBrief', 'intake_cli',
    'decompose_brief', 'integrate_research', 'ArchitectureTeamPlan', 'arch_team_cli',
    'execute_research', 'save_result', 'ResearchResult', 'research_cli',
    'TaskContract', 'CriticContract', 'LeadContract', 'LeadResult',
    'create_implementation_contract', 'create_critic_contract', 'create_lead_contract',
    'validate_contract', 'save_contract', 'load_contract', 'list_contracts', 'task_contracts_cli',
    'build_project_view', 'save_project_view', 'project_view_cli',
    'CriticReport', 'Reviewer', 'Coverage', 'Finding', 'parse_critic_report',
    'validate_critic_report', 'report_prompt',
    'run_department_lead', 'validate_lead_plan', 'parse_json_object', 'lead_execution_cli',
    'run_implementer', 'run_critic', 'repair_loop', 'pair_execution_cli',
    'collect_reviewed_tasks', 'run_integration_tests', 'generate_integration_report', 'save_integration_report', 'integration_cli',
]
