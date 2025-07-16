#!/usr/bin/env python3
"""NOAH Infrastructure Deployment

This Python script replaces the previous Bash implementation and deploys the
core services for the Next Open-source Architecture Hub.
"""
import os
import shutil
import subprocess
import argparse
import logging
from datetime import datetime
from pathlib import Path

PROJECT_DESC = (
    "N.O.A.H - Next Open-source Architecture Hub "
    "infrastructure deployment script"
)

MIN_CPU = 2
MIN_MEM_GB = 4

BASE_DIR = Path(__file__).resolve().parent.parent
HELM_DIR = BASE_DIR / "Helm"
VALUES_ROOT = HELM_DIR / "values" / "values-root.yaml"
LOG_DIR = BASE_DIR / "logs"
DEPLOY_DIR = LOG_DIR / "deployments"
ERROR_DIR = LOG_DIR / "errors"

DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = DEPLOY_DIR / f"deployment_{timestamp}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )
    err_handler = logging.FileHandler(ERROR_DIR / f"errors_{timestamp}.log")
    err_handler.setLevel(logging.ERROR)
    logging.getLogger().addHandler(err_handler)
    return log_file


def check_root():
    if os.geteuid() != 0:
        raise SystemExit("This script must be run as root.")


def get_total_memory_gb():
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return kb / 1024 / 1024
    except FileNotFoundError:
        return 0
    return 0


def check_infrastructure():
    cpu = os.cpu_count() or 0
    mem = get_total_memory_gb()
    if cpu < MIN_CPU or mem < MIN_MEM_GB:
        logging.error(
            "Insufficient resources: CPU=%s cores, MEM=%.1fGB",
            cpu,
            mem,
        )
        raise SystemExit("Infrastructure requirements not met.")
    logging.info("Infrastructure OK: CPU=%s cores MEM=%.1fGB", cpu, mem)


def check_prerequisites():
    required = ["ansible-playbook", "helm", "docker", "minikube"]
    missing = [cmd for cmd in required if shutil.which(cmd) is None]
    if missing:
        logging.error(
            "Missing prerequisites: %s",
            ", ".join(missing),
        )
        raise SystemExit("Install required tools and try again.")
    logging.info("All prerequisites found")


def deploy_chart(
    chart: str,
    namespace: str,
    values: Path,
    dry_run: bool = False,
):
    chart_path = HELM_DIR / chart
    if not chart_path.exists():
        logging.warning("Chart %s not found, skipping", chart)
        return
    release = chart
    cmd = [
        "helm",
        "upgrade",
        "--install",
        release,
        str(chart_path),
        "-n",
        namespace,
        "--create-namespace",
        "-f",
        str(values),
    ]
    if dry_run:
        cmd.append("--dry-run")
    logging.info("Deploying %s", chart)
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        logging.error(
            "Deployment failed for %s: %s",
            chart,
            exc.stderr,
        )
        raise


def main():
    parser = argparse.ArgumentParser(
        description="NOAH Infrastructure Deployment",
    )
    parser.add_argument("action", choices=["deploy"], help="Action to perform")
    parser.add_argument("--namespace", default="noah")
    parser.add_argument("--values", default=str(VALUES_ROOT))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(PROJECT_DESC)
    log_file = setup_logging()
    logging.info("Log file: %s", log_file)

    check_root()
    check_infrastructure()
    check_prerequisites()

    if args.action == "deploy":
        charts = []
        if (HELM_DIR / "noah-common").exists():
            charts.append("noah-common")
        charts.extend(["samba4", "keycloak", "oauth2-proxy"])
        for chart in charts:
            try:
                deploy_chart(
                    chart,
                    args.namespace,
                    Path(args.values),
                    args.dry_run,
                )
            except subprocess.CalledProcessError:
                logging.error("Aborting due to previous error")
                break


if __name__ == "__main__":
    main()
