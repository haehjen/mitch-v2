import json
import re
from datetime import datetime
from pathlib import Path

from core.config import MITCH_ROOT
from core.event_bus import event_bus
from core.peterjones import get_logger
from modules.file_ingestor import _classify, extract_html_text, extract_pdf_text, extract_text_file

logger = get_logger("nssr_designer")

NSSR_ROOT = Path(MITCH_ROOT) / "data" / "nssr"
CLIENTS_DIR = NSSR_ROOT / "clients"
RUNS_DIR = NSSR_ROOT / "runs"
TEMPLATES_DIR = NSSR_ROOT / "templates"
UPLOADS_DIR = Path(MITCH_ROOT) / "uploads"

ESTATE_FILENAMES = ("estate.md", "current_estate.md", "estate.txt")
RATE_FILENAMES = ("resource_rates.md", "rates.md", "resource_rates.txt", "rates.txt")
CLIENT_CONTEXT_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".html", ".htm"}
DEFAULT_TEMPLATE = "nssr_solution_template.md"

STAGE_TRR = "trr"
STAGE_GAP = "gap"
STAGE_SOLUTION = "solution"
STAGE_SEQUENCE = [STAGE_TRR, STAGE_GAP, STAGE_SOLUTION]


class NSSRDesigner:
    def __init__(self):
        CLIENTS_DIR.mkdir(parents=True, exist_ok=True)
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        self.pending_runs = {}
        self.chains = {}

    def handle_file_ready(self, data):
        payload = data if isinstance(data, dict) else {}
        filename = str(payload.get("filename", "") or "").strip()
        if not filename or not self._is_nssr_filename(filename):
            return

        upload_path = UPLOADS_DIR / filename
        if not upload_path.exists():
            logger.warning("NSSR upload not found on disk: %s", upload_path)
            return

        client_id = self._resolve_client_id(filename)
        if not client_id:
            self._emit_status(
                "NSSR upload detected, but I could not match it to a client. "
                "Use a filename like 'NSSR_client-slug_request.pdf' or create only one client folder under data/nssr/clients."
            )
            return

        requested_stage = self._resolve_requested_stage(filename)
        start_stage = requested_stage or STAGE_TRR
        pipeline_mode = "single_stage" if requested_stage else "full_pipeline"

        estate_path = self._find_client_doc(client_id, ESTATE_FILENAMES)
        rates_path = self._find_client_doc(client_id, RATE_FILENAMES)
        template_path = TEMPLATES_DIR / DEFAULT_TEMPLATE

        missing = []
        if not estate_path:
            missing.append(f"Missing estate document for client '{client_id}'.")
        if not rates_path:
            missing.append(f"Missing resource rates document for client '{client_id}'.")
        if not template_path.exists():
            missing.append(f"Missing NSSR solution template: {template_path}.")

        nssr_text = self._extract_upload_text(upload_path)
        if not nssr_text.strip():
            missing.append(f"Unable to read NSSR content from {filename}.")

        estate_text = self._read_text(estate_path)
        rates_text = self._read_text(rates_path)
        template_text = self._read_text(template_path)
        extra_docs = self._load_extra_client_docs(client_id, exclude={estate_path, rates_path})
        nssr_summary = self._summarise_nssr_text(nssr_text)

        retrieved_context = self._build_context(
            client_id=client_id,
            filename=filename,
            nssr_text=nssr_text,
            estate_path=estate_path,
            estate_text=estate_text,
            rates_path=rates_path,
            rates_text=rates_text,
            template_path=template_path,
            template_text=template_text,
            extra_docs=extra_docs,
            missing=missing,
        )

        prompt = self._build_prompt(
            stage=start_stage,
            filename=filename,
            client_id=client_id,
            nssr_summary=nssr_summary,
            template_text=template_text,
            missing=missing,
        )

        chain_id = self._new_chain_id(client_id, filename)
        token = self._new_token()
        retrieved_context = self._build_stage_context(retrieved_context, {})
        run_files = self._write_run_files(
            chain_id=chain_id,
            client_id=client_id,
            filename=filename,
            stage=start_stage,
            prompt=prompt,
            summary=nssr_summary,
            retrieved_context=retrieved_context,
            missing=missing,
        )
        self.chains[chain_id] = {
            "chain_id": chain_id,
            "client_id": client_id,
            "filename": filename,
            "pipeline_mode": pipeline_mode,
            "requested_stage": requested_stage,
            "current_stage": start_stage,
            "nssr_summary": nssr_summary,
            "template_text": template_text,
            "base_context": retrieved_context,
            "missing": missing,
            "stage_outputs": {},
            "stage_files": {start_stage: run_files},
        }
        self.pending_runs[token] = {
            "chain_id": chain_id,
            "stage": start_stage,
            "run_files": run_files,
        }

        event_bus.emit(
            "EMIT_CHAT_REQUEST",
            {
                "token": token,
                "prompt": prompt,
                "retrieved_context": retrieved_context,
                "request_type": "nssr_rag",
                "stage": start_stage,
            },
        )

        logger.info(
            "Prepared NSSR request for client=%s stage=%s mode=%s file=%s",
            client_id,
            start_stage,
            pipeline_mode,
            filename,
        )

    def _resolve_requested_stage(self, filename: str) -> str:
        lowered = filename.lower()
        if ".trr." in lowered or "_trr" in lowered or "-trr" in lowered:
            return STAGE_TRR
        if ".gap." in lowered or "_gap" in lowered or "-gap" in lowered:
            return STAGE_GAP
        if ".solution." in lowered or "_solution" in lowered or "-solution" in lowered:
            return STAGE_SOLUTION
        return ""

    def _shared_rules(self) -> str:
        return """
You are a senior Solution Integrator.

Use the supplied retrieved context as the source of truth for the client estate, rates, and supporting files.

Rules:
- Do NOT produce generic statements where the estate supports a concrete design.
- Do NOT invent missing information.
- Prefer implementation-level detail over abstract wording.
- Every recommendation must be grounded in the estate or NSSR.
- If multiple workstreams exist, separate them before producing a combined view.
- If something is not required, say so explicitly and explain why.
""".strip()

    def _build_prompt(
        self,
        stage: str,
        filename: str,
        client_id: str,
        nssr_summary: str,
        template_text: str,
        missing: list[str],
    ) -> str:
        if stage == STAGE_TRR:
            return self._build_trr_prompt(filename, client_id, nssr_summary, missing)
        if stage == STAGE_GAP:
            return self._build_gap_prompt(filename, client_id, nssr_summary, missing)
        return self._build_solution_prompt(filename, client_id, nssr_summary, template_text, missing)

    def _build_trr_prompt(
        self,
        filename: str,
        client_id: str,
        nssr_summary: str,
        missing: list[str],
    ) -> str:
        gap_instruction = (
            "List only the missing details that need to be asked during the technical requirements review."
            if missing
            else "Do not repeat obvious facts already present in the estate."
        )

        return f"""
{self._shared_rules()}

Mode: Technical Requirements Review

Review the NSSR '{filename}' for client '{client_id}'.

NSSR summary:
{nssr_summary}

Task:
Generate the technical requirements review questions that must be answered before confident solution design and costing.

Requirements:
- Group questions by workstream.
- Prioritise blocking technical questions first.
- Do not produce a final solution.
- Do not produce costs.
- Do not repeat information already known from the supplied estate.
- Be specific about networking, identity, endpoint management, security, support, and delivery dependencies.
- Where appropriate, ask for quantities, hosting choices, authentication method, onboarding model, backup expectations, and operational ownership.

{gap_instruction}

Output format:

# Technical Requirements Review

## Workstreams
- List the workstreams identified in the NSSR

## Blocking Questions
1.
2.
3.

## Non-Blocking Clarifications
1.
2.
3.
""".strip()

    def _build_gap_prompt(
        self,
        filename: str,
        client_id: str,
        nssr_summary: str,
        missing: list[str],
    ) -> str:
        return f"""
{self._shared_rules()}

Mode: Gap Analysis

Review the NSSR '{filename}' for client '{client_id}'.

NSSR summary:
{nssr_summary}

Task:
Identify what is known, what can be reasonably inferred from the estate, and what is still missing before a confident design or cost can be produced.

Requirements:
- Separate distinct workstreams first.
- Do not produce a full solution.
- Do not fill tables with placeholders.
- Be explicit about blockers vs non-blockers.
- Where a likely implementation direction exists, state it as a likely path, but do not present it as final design.
- Highlight estate constraints, delivery constraints, licensing uncertainty, support uncertainty, and missing operational detail.

Output format:

# NSSR Gap Analysis

## Workstreams
- List each workstream

## Known Facts
- Item
- Item

## Likely Inferences
- Item
- Item

## Blocking Gaps
- Item
- Item

## Non-Blocking Gaps
- Item
- Item

## Design Risks
- Item
- Item
""".strip()

    def _build_solution_prompt(
        self,
        filename: str,
        client_id: str,
        nssr_summary: str,
        template_text: str,
        missing: list[str],
    ) -> str:
        gap_instruction = (
            "Start with a short 'Missing Information' section listing only blocking gaps."
            if missing
            else "If any blocking detail is absent, add a short 'Missing Information' section instead of guessing."
        )

        return f"""
{self._shared_rules()}

Mode: Final NSSR Solution

Review the NSSR '{filename}' for client '{client_id}'.

NSSR summary:
{nssr_summary}

Task:
Produce a practical project-style response covering likely work required, estate impact, implementation choices, resource considerations, and delivery assumptions.

Process:
1. Identify the distinct workstreams in the NSSR.
2. Assess likely implementation choices that fit the known estate.
3. Produce a combined final solution using the required template.

Strict requirements:
- Do NOT output empty tables.
- Do NOT output placeholder rows containing 'TBC' unless absolutely unavoidable.
- If no infrastructure is required, explicitly state "No new infrastructure required" and explain why.
- Treat explicit NSSR preferences and stated scope as higher priority than your own inference unless the estate clearly makes them infeasible.
- If the NSSR explicitly asks for new physical hosts, do not silently convert that into new virtual machines. If you recommend VMs instead, present that as an alternative and explain why it departs from the stated preference.
- Distinguish clearly between:
  - new physical hosts
  - new virtual machines on existing virtualization platforms
  - reuse of existing servers
  Never describe a VM-based design as a physical-host deployment.
- Every recommendation must include:
  - why it was chosen
  - what in the estate supports it
  - what risk exists if the assumption is wrong
- If TRR or gap analysis identified a blocker that is still unresolved, mark the relevant recommendation as provisional pending confirmation instead of presenting it as fully confirmed.
- For connectivity, include likely source/destination flows, protocols, and real port numbers where relevant.
- If the design uses a secure portal, gateway, reverse proxy, or web access layer, describe the access pattern accordingly and do not collapse it into generic direct RDP access.
- Do not expose TCP 3389 from user devices to RDS hosts unless the source explicitly supports that design choice.
- For identity, explicitly describe Active Directory, Entra ID, hybrid identity, SSO, sync, service accounts, groups, and delegated permissions where relevant.
- For implementation, describe actual tasks such as packaging, deployment, firewall changes, DNS, certificates, NAT/public exposure, backup onboarding, monitoring onboarding, testing, rollback, documentation, and operational handover.
- For delivery, map work to the most appropriate roles from the supplied rates/context.
- For costs, separate one-off and recurring costs.
- For recurring costs, explicitly include support and management charges for each proposed VM, host, appliance, or service where the supplied client cost files support that calculation.
- Show the monthly pricing basis for recurring items, then provide a recurring monthly subtotal or total.
- If pricing data is incomplete, say "Not yet costed".
- If multiple workstreams exist, analyse them separately and then produce a combined solution.
- For RDS, remote access, or published application scenarios, explicitly consider whether additional components are required, such as gateway, broker, licensing, profile management, DNS, certificate, or web access roles.

{gap_instruction}

Required output template:
{template_text or "(template missing)"}
""".strip()

    def _build_context(
        self,
        client_id: str,
        filename: str,
        nssr_text: str,
        estate_path: Path | None,
        estate_text: str,
        rates_path: Path | None,
        rates_text: str,
        template_path: Path | None,
        template_text: str,
        extra_docs: list[dict],
        missing: list[str],
    ) -> str:
        lines = [
            "# NSSR Supporting Context",
            "",
            f"Client: {client_id}",
            f"Uploaded NSSR: {filename}",
            "",
            "## Missing Information",
        ]
        if missing:
            lines.extend(f"- {item}" for item in missing)
        else:
            lines.append("- No missing source documents were detected.")

        lines.extend(
            [
                "",
                "## Uploaded NSSR Source",
                nssr_text or "(uploaded NSSR text missing)",
                "",
                "## Client Estate",
                f"Source: {estate_path}" if estate_path else "Source: (missing)",
                estate_text or "(estate document missing)",
                "",
                "## Resource Rates",
                f"Source: {rates_path}" if rates_path else "Source: (missing)",
                rates_text or "(resource rates document missing)",
                "",
                "## Required Output Template",
                f"Source: {template_path}" if template_path and template_path.exists() else "Source: (missing)",
                template_text or "(solution template missing)",
            ]
        )

        if extra_docs:
            lines.extend(["", "## Additional Client Context"])
            for doc in extra_docs:
                lines.extend(
                    [
                        f"### {doc['name']}",
                        f"Source: {doc['path']}",
                        doc["content"],
                    ]
                )

        return "\n".join(lines).strip()

    def _build_stage_context(self, base_context: str, stage_outputs: dict[str, str]) -> str:
        lines = [base_context.strip()]
        if stage_outputs:
            lines.extend(["", "## Prior Stage Outputs"])
            for stage_name in STAGE_SEQUENCE:
                output = str(stage_outputs.get(stage_name, "") or "").strip()
                if not output:
                    continue
                lines.extend(
                    [
                        f"### {stage_name.upper()}",
                        output,
                    ]
                )
        return "\n".join(lines).strip()

    def _write_run_files(
        self,
        chain_id: str,
        client_id: str,
        filename: str,
        stage: str,
        prompt: str,
        summary: str,
        retrieved_context: str,
        missing: list[str],
    ) -> dict:
        base = f"{chain_id}_{stage}"

        context_file = RUNS_DIR / f"{base}_context.md"
        prompt_file = RUNS_DIR / f"{base}_prompt.md"
        meta_file = RUNS_DIR / f"{base}_meta.json"
        response_file = RUNS_DIR / f"{base}_response.md"
        final_file = RUNS_DIR / f"{base}_final.md"

        context_file.write_text(retrieved_context, encoding="utf-8")
        prompt_file.write_text(prompt, encoding="utf-8")
        meta_file.write_text(
            json.dumps(
                {
                    "chain_id": chain_id,
                    "client_id": client_id,
                    "filename": filename,
                    "stage": stage,
                    "nssr_summary": summary,
                    "missing": missing,
                    "context_file": str(context_file),
                    "prompt_file": str(prompt_file),
                    "response_file": str(response_file),
                    "final_file": str(final_file),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        return {
            "chain_id": chain_id,
            "client_id": client_id,
            "filename": filename,
            "stage": stage,
            "context_file": context_file,
            "prompt_file": prompt_file,
            "meta_file": meta_file,
            "response_file": response_file,
            "final_file": final_file,
            "missing": missing,
        }

    def _resolve_client_id(self, filename: str) -> str:
        available = [path.name for path in CLIENTS_DIR.iterdir() if path.is_dir()]
        lowered = filename.lower()

        for client_id in sorted(available, key=len, reverse=True):
            if client_id.lower() in lowered:
                return client_id

        if len(available) == 1:
            return available[0]

        match = re.match(r"^nssr[-_ ]+([a-z0-9][a-z0-9_-]*)", Path(filename).stem, re.IGNORECASE)
        if match:
            candidate = match.group(1).lower()
            if candidate in {item.lower() for item in available}:
                return next(item for item in available if item.lower() == candidate)

        return ""

    def _find_client_doc(self, client_id: str, candidates: tuple[str, ...]) -> Path | None:
        client_dir = CLIENTS_DIR / client_id
        if not client_dir.exists():
            return None

        for name in candidates:
            path = client_dir / name
            if path.exists() and path.is_file():
                return path

        return None

    def _extract_upload_text(self, path: Path) -> str:
        kind = _classify(None, path.name)
        result = {}

        if kind == "pdf":
            result = extract_pdf_text(path)
        elif kind == "html":
            result = extract_html_text(path)
        else:
            result = extract_text_file(path)

        return str(result.get("text", "") or "").strip()

    def _load_extra_client_docs(self, client_id: str, exclude: set[Path | None]) -> list[dict]:
        client_dir = CLIENTS_DIR / client_id
        if not client_dir.exists():
            return []

        excluded = {path.resolve() for path in exclude if path}
        docs = []

        for path in sorted(client_dir.iterdir()):
            if not path.is_file():
                continue
            if path.resolve() in excluded:
                continue
            if path.suffix.lower() not in CLIENT_CONTEXT_EXTENSIONS:
                continue

            content = self._read_text(path)
            if len(content) > 12000:
                content = content[:12000] + "\n\n[truncated for context size]"

            docs.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "content": content or "(empty file)",
                }
            )

        return docs

    def _summarise_nssr_text(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
        if not cleaned:
            return "(NSSR text could not be extracted.)"

        limit = 2400
        if len(cleaned) <= limit:
            return cleaned

        return cleaned[:limit] + " ..."

    def _read_text(self, path: Path | None) -> str:
        if not path:
            return ""

        try:
            return path.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception as exc:
            logger.warning("Failed to read %s: %s", path, exc)
            return f"(failed to read {path.name}: {exc})"

    def _is_nssr_filename(self, filename: str) -> bool:
        stem = Path(filename).stem
        return bool(re.match(r"^nssr[-_ ]", stem, re.IGNORECASE))

    def _emit_status(self, text: str):
        token = self._new_token()
        event_bus.emit("EMIT_TOKEN_REGISTERED", {"token": token})
        event_bus.emit("EMIT_VISUAL_TOKEN", {"token": token})
        event_bus.emit("EMIT_SPEAK", {"text": text, "token": token, "source": "nssr_designer"})
        event_bus.emit("EMIT_SPEAK_END", {"token": token, "full_text": text})

    def handle_speak_end(self, data):
        payload = data if isinstance(data, dict) else {}
        token = str(payload.get("token", "") or "").strip()
        if not token or token not in self.pending_runs:
            return

        pending = self.pending_runs.pop(token)
        chain_id = pending["chain_id"]
        stage = pending["stage"]
        run_files = pending["run_files"]
        response_text = str(payload.get("full_text", "") or "").strip()
        if not response_text:
            response_text = "(No response text was captured from the assistant.)"

        run_files["response_file"].write_text(response_text + "\n", encoding="utf-8")
        chain = self.chains.get(chain_id)
        if not chain:
            logger.warning("Missing NSSR chain state for token=%s chain=%s", token, chain_id)
            return

        chain["stage_outputs"][stage] = response_text
        chain["stage_files"][stage] = run_files

        next_stage = self._next_stage(chain, stage)
        if next_stage:
            next_token = self._new_token()
            next_context = self._build_stage_context(chain["base_context"], chain["stage_outputs"])
            next_prompt = self._build_prompt(
                stage=next_stage,
                filename=chain["filename"],
                client_id=chain["client_id"],
                nssr_summary=chain["nssr_summary"],
                template_text=chain["template_text"],
                missing=chain["missing"],
            )
            next_run_files = self._write_run_files(
                chain_id=chain_id,
                client_id=chain["client_id"],
                filename=chain["filename"],
                stage=next_stage,
                prompt=next_prompt,
                summary=chain["nssr_summary"],
                retrieved_context=next_context,
                missing=chain["missing"],
            )
            chain["current_stage"] = next_stage
            chain["stage_files"][next_stage] = next_run_files
            self.pending_runs[next_token] = {
                "chain_id": chain_id,
                "stage": next_stage,
                "run_files": next_run_files,
            }
            event_bus.emit(
                "EMIT_CHAT_REQUEST",
                {
                    "token": next_token,
                    "prompt": next_prompt,
                    "retrieved_context": next_context,
                    "request_type": "nssr_rag",
                    "stage": next_stage,
                },
            )
            logger.info("Queued NSSR next stage for chain=%s stage=%s", chain_id, next_stage)
            return

        final_doc = "\n".join(
            [
                "# NSSR Output",
                "",
                f"Client: {chain['client_id']}",
                f"Uploaded NSSR: {chain['filename']}",
                f"Pipeline Mode: {chain['pipeline_mode']}",
                "",
                "## Stage Outputs",
            ]
        )
        for stage_name in STAGE_SEQUENCE:
            output = str(chain["stage_outputs"].get(stage_name, "") or "").strip()
            if not output:
                continue
            stage_files = chain["stage_files"].get(stage_name) or {}
            final_doc.extend(
                [
                    "",
                    f"### {stage_name.upper()}",
                    output,
                    "",
                    "Source Files:",
                    f"- Prompt: {stage_files.get('prompt_file')}",
                    f"- Context: {stage_files.get('context_file')}",
                    f"- Metadata: {stage_files.get('meta_file')}",
                    f"- Response: {stage_files.get('response_file')}",
                ]
            )
        final_doc = "\n".join(final_doc).strip() + "\n"

        run_files["final_file"].write_text(final_doc, encoding="utf-8")
        self.chains.pop(chain_id, None)
        logger.info("Saved NSSR final output to %s", run_files["final_file"])

    def _new_token(self) -> str:
        return str(int(datetime.utcnow().timestamp() * 1_000_000))

    def _new_chain_id(self, client_id: str, filename: str) -> str:
        stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        stem = Path(filename).stem
        safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("_") or "nssr"
        return f"{stamp}_{client_id}_{safe_stem}"

    def _next_stage(self, chain: dict, completed_stage: str) -> str:
        if chain.get("pipeline_mode") != "full_pipeline":
            return ""
        try:
            idx = STAGE_SEQUENCE.index(completed_stage)
        except ValueError:
            return ""
        next_idx = idx + 1
        if next_idx >= len(STAGE_SEQUENCE):
            return ""
        return STAGE_SEQUENCE[next_idx]


nssr_designer = NSSRDesigner()


def start_module(event_bus):
    event_bus.subscribe("EMIT_FILE_READY", nssr_designer.handle_file_ready)
    event_bus.subscribe("EMIT_SPEAK_END", nssr_designer.handle_speak_end)
    logger.info("nssr_designer started.")
