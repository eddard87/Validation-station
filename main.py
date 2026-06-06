"""
Generali Corporate Commercial - AI Data Platform
Entry point for running the OrchestratorAgent from the command line.

Usage:
    python main.py --task "Run full daily pipeline"
    python main.py --task "Check data quality for Silver claims layer"
    python main.py --task "Refresh claim_propensity feature store"
    python main.py --pipeline daily
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import yaml
import structlog
from dotenv import load_dotenv

load_dotenv()

logging = structlog.get_logger(__name__)


def load_configs() -> tuple[dict, dict]:
    with open("config/agents.yaml") as f:
        agent_cfg = yaml.safe_load(f)
    with open("config/fabric.yaml") as f:
        fabric_cfg = yaml.safe_load(f)
    return agent_cfg, fabric_cfg


def run_orchestrator(task: str, context: dict | None = None) -> None:
    from agents.orchestrator import OrchestratorAgent
    agent_cfg, fabric_cfg = load_configs()
    orchestrator = OrchestratorAgent(agent_cfg, fabric_cfg)
    print(f"\nRunning task: {task}\n{'='*60}")
    result = orchestrator.run(task=task, context=context, task_id="cli-run")
    print(f"\nStatus: {result.status.value}")
    print(f"Duration: {result.duration_seconds:.1f}s")
    if result.output:
        print(f"\nOutput:\n{result.output}")
    if result.error:
        print(f"\nError: {result.error}", file=sys.stderr)
        sys.exit(1)


def run_daily_pipeline() -> None:
    from orchestration.task_manager import TaskManager
    from agents.orchestrator import OrchestratorAgent
    agent_cfg, fabric_cfg = load_configs()
    orchestrator = OrchestratorAgent(agent_cfg, fabric_cfg)

    def dispatcher(agent_name: str, task_description: str, context: dict) -> dict:
        result = orchestrator._agents[agent_name].run(
            task=task_description, context=context, task_id=f"dag-{agent_name}"
        )
        if not result.succeeded():
            raise RuntimeError(result.error or "Task failed")
        return {"status": "succeeded", "output": result.output}

    manager = TaskManager()
    manager.add_daily_pipeline_tasks()
    print("\nRunning daily pipeline...\n")
    summary = manager.execute(dispatcher)
    print(json.dumps(summary, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generali AI Data Platform CLI")
    parser.add_argument("--task", type=str, help="Natural language task for the OrchestratorAgent")
    parser.add_argument("--pipeline", choices=["daily"], help="Run a pre-defined pipeline")
    parser.add_argument("--health", action="store_true", help="Check platform health")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    if args.health:
        run_orchestrator("Check platform health and return a summary of all component statuses.")
    elif args.pipeline == "daily":
        run_daily_pipeline()
    elif args.task:
        run_orchestrator(args.task)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
