"""Insight agent: curriculum analysis; optional OpenAI / Gemini LLM layer over deterministic metrics."""

from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path
from statistics import mean
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
import requests

from orchestrator.state import ClassroomState
from settings import get_settings

logger = logging.getLogger(__name__)

INSIGHT_SYSTEM_PROMPT = """You are the Insight Agent for kari.ai, a curriculum simulation.

You receive ONLY structured JSON: curriculum metadata, module_results from assessors, final student roster, and precomputed metrics (confusion map, ordering hints, Bloom flags, archetypes, at-risk list).

Your job:
1) Synthesize an educator-facing curriculum report grounded in that data. Do not invent students, scores, or events not present in the input.
2) If data is thin, say so briefly and still use what exists.
3) No medical or clinical diagnoses. Learning patterns are OK when tied to the data.
4) Bloom labels: 1 Remember, 2 Understand, 3 Apply, 4 Analyse, 5 Evaluate, 6 Create.
5) Write in a paper-like style with substantial depth. Prefer analytical prose over short bullets.

Return STRICT JSON only (no markdown fences) with this schema:
{
  "summary": "string, 3-6 sentences executive summary",
  "curriculum_critique": "string, markdown in long-form paper style with sections: ## ABSTRACT\\n...\\n## METHODOLOGY\\n...\\n## RESULTS\\n...\\n## CONFUSION TREND ANALYSIS\\n...\\n## CONCEPT ORDERING ANALYSIS\\n...\\n## BLOOM ALIGNMENT ANALYSIS\\n...\\n## ARCHETYPE PERFORMANCE\\n...\\n## AT-RISK LEARNERS\\n...\\n## RECOMMENDATIONS\\n...\\n## LIMITATIONS\\n...",
  "blooms_alignment_notes": ["string"],
  "concept_ordering_issues": ["string"],
  "recommendations": [
    {"priority": "high | medium | low", "target": "curriculum | module | assessment | pedagogy", "action": "string"}
  ]
}

Use precomputed fields as authoritative signals; refine wording and add actionable recommendations."""

_MAX_IMAGE_TEXT_CHARS = 700


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _confusion_severity(conf_pct: float) -> str:
    if conf_pct >= 75:
        return "critical"
    if conf_pct >= 55:
        return "high"
    if conf_pct >= 35:
        return "medium"
    return "low"


def _collect_assessor_logs(state: ClassroomState) -> list[dict]:
    logs = [l for l in state["timestep_logs"] if l.get("agent") == "assessor"]
    logs.sort(key=lambda l: (int(l.get("module_index", -1)), int(l.get("timestep", -1))))
    return logs


def _module_confusion_map(state: ClassroomState, assessor_logs: list[dict]) -> list[dict]:
    modules = state["curriculum"].get("modules") or []
    per_module: dict[int, list[float]] = {i: [] for i in range(len(modules))}

    for log in assessor_logs:
        m = int(log.get("module_index", -1))
        payload = log.get("payload") or {}
        if m in per_module:
            per_module[m].append(_to_float(payload.get("avg_confusion"), 0.0))

    result: list[dict] = []
    for i, mod in enumerate(modules):
        vals = per_module.get(i) or []
        conf = (mean(vals) if vals else 0.0) * 100.0
        result.append(
            {
                "module_index": i,
                "module_id": mod.get("id", f"m{i}"),
                "title": mod.get("title", f"Module {i + 1}"),
                "avg_confusion_pct": round(conf, 2),
                "severity": _confusion_severity(conf),
            }
        )
    return result


def _concept_ordering_issues(confusion_map: list[dict]) -> list[str]:
    issues: list[str] = []
    for i in range(1, len(confusion_map)):
        prev_conf = confusion_map[i - 1]["avg_confusion_pct"]
        cur = confusion_map[i]
        cur_conf = cur["avg_confusion_pct"]
        if cur_conf >= 70 and (cur_conf - prev_conf) >= 15:
            issues.append(
                f"Module {cur['module_index'] + 1} ({cur['title']}) has a confusion spike "
                f"({cur_conf:.1f}% vs {prev_conf:.1f}% previous module). "
                "Likely prerequisite gap or concept ordering problem."
            )
    return issues


def _blooms_alignment_notes(state: ClassroomState, confusion_map: list[dict]) -> list[str]:
    modules = state["curriculum"].get("modules") or []
    conf_by_index = {row["module_index"]: row["avg_confusion_pct"] for row in confusion_map}
    notes: list[str] = []

    for i, mod in enumerate(modules):
        blooms = int(mod.get("blooms_level", 0) or 0)
        content = str(mod.get("content") or "").lower()
        has_exercise_signal = any(k in content for k in ["exercise", "lab", "project", "hands-on", "coding"])
        conf = conf_by_index.get(i, 0.0)

        if blooms >= 3 and not has_exercise_signal:
            notes.append(
                f"Module {i + 1} targets Bloom level {blooms} but lacks exercise/project signals."
            )
        if blooms >= 4 and conf >= 60:
            notes.append(
                f"Module {i + 1} aims at higher-order Bloom level ({blooms}) with high confusion ({conf:.1f}%)."
            )
    return notes


def _archetype_performance(students: list[dict], module_results: list[dict]) -> dict[str, float]:
    latest_scores: dict[str, float] = {}
    for result in module_results:
        for sid, score in (result.get("student_scores") or {}).items():
            latest_scores[str(sid)] = _to_float(score, 0.0)

    buckets: dict[str, list[float]] = {}
    for s in students:
        sid = str(s.get("id"))
        style = str(s.get("learning_style") or "unknown")
        score = latest_scores.get(sid)
        if score is None:
            ks = s.get("knowledge_state") or {}
            vals = [_to_float(v, 0.0) for v in ks.values()]
            score = (mean(vals) if vals else 0.0) * 100.0
        buckets.setdefault(style, []).append(score)

    return {style: round(mean(vals), 2) for style, vals in buckets.items() if vals}


def _at_risk_students(students: list[dict], module_results: list[dict]) -> list[dict]:
    risk_counts: dict[str, int] = {}
    for res in module_results:
        for sid in res.get("at_risk_student_ids") or []:
            risk_counts[str(sid)] = risk_counts.get(str(sid), 0) + 1

    roster = {str(s.get("id")): s for s in students}
    out: list[dict] = []
    for sid, cnt in sorted(risk_counts.items(), key=lambda kv: kv[1], reverse=True):
        student = roster.get(sid, {})
        out.append(
            {
                "id": sid,
                "name": student.get("name", sid),
                "learning_style": student.get("learning_style", "unknown"),
                "risk_hits": cnt,
                "misconceptions_remaining": list(student.get("misconceptions") or []),
            }
        )
    return out


def _render_text_report(
    title: str,
    n_students: int,
    n_modules: int,
    confusion_map: list[dict],
    ordering_issues: list[str],
    blooms_notes: list[str],
    archetypes: dict[str, float],
    at_risk: list[dict],
) -> str:
    lines: list[str] = []
    lines.append(f"CURRICULUM ANALYSIS — {title}")
    lines.append(f"Simulation: {n_students} students × {n_modules} modules")
    lines.append("")
    lines.append("CONFUSION MAP")
    for row in confusion_map:
        title_m = row["title"]
        conf = row["avg_confusion_pct"]
        bars = "░" * max(1, int(round(conf / 5)))
        sev = row["severity"]
        marker = " ❌" if sev == "critical" else (" ⚠️" if sev == "high" else "")
        lines.append(f"M{row['module_index'] + 1} {title_m:<18} {bars} {conf:.0f}%{marker}")

    lines.append("")
    lines.append("CONCEPT ORDERING ISSUES")
    if ordering_issues:
        lines.extend([f"- {issue}" for issue in ordering_issues])
    else:
        lines.append("- No major ordering spikes detected from confusion trends.")

    lines.append("")
    lines.append("BLOOM'S ALIGNMENT ISSUES")
    if blooms_notes:
        lines.extend([f"- {note}" for note in blooms_notes])
    else:
        lines.append("- No obvious Bloom mismatch flags from current module metadata.")

    lines.append("")
    lines.append("STUDENT ARCHETYPE PERFORMANCE")
    if archetypes:
        for style, avg_score in sorted(archetypes.items()):
            badge = "✅" if avg_score >= 65 else ("⚠️" if avg_score >= 45 else "❌")
            lines.append(f"- {style:<12} avg retention: {avg_score:.1f}% {badge}")
    else:
        lines.append("- No archetype data available.")

    lines.append("")
    lines.append("AT-RISK STUDENTS")
    if at_risk:
        for entry in at_risk[:8]:
            rem = entry["misconceptions_remaining"]
            extra = f" | misconceptions: {', '.join(rem[:2])}" if rem else ""
            lines.append(
                f"- {entry['name']} ({entry['learning_style']}, risk_hits={entry['risk_hits']}){extra}"
            )
    else:
        lines.append("- No students flagged as at-risk.")

    return "\n".join(lines)


def _student_roster_for_insight(students: list[dict]) -> list[dict]:
    """Traits allowed for insight (not for assessor)."""
    out: list[dict] = []
    for s in students:
        out.append(
            {
                "id": s.get("id"),
                "name": s.get("name"),
                "learning_style": s.get("learning_style"),
                "attention_span_mins": s.get("attention_span_mins"),
                "social_anxiety": s.get("social_anxiety"),
                "motivation": s.get("motivation"),
                "peer_influence": s.get("peer_influence"),
                "knowledge_state": dict(s.get("knowledge_state") or {}),
                "misconceptions": list(s.get("misconceptions") or []),
                "confusion_level": s.get("confusion_level"),
                "cumulative_fatigue": s.get("cumulative_fatigue"),
            }
        )
    return out


def _build_insight_report(state: ClassroomState) -> dict[str, Any]:
    """Deterministic `insight_report` payload only."""
    curriculum = state["curriculum"]
    modules = curriculum.get("modules") or []
    students = state["students"]
    module_results = sorted(state["module_results"], key=lambda r: int(r.get("module_index", -1)))
    assessor_logs = _collect_assessor_logs(state)

    confusion_map = _module_confusion_map(state, assessor_logs)
    ordering_issues = _concept_ordering_issues(confusion_map)
    blooms_notes = _blooms_alignment_notes(state, confusion_map)
    archetype_perf = _archetype_performance(students, module_results)
    at_risk = _at_risk_students(students, module_results)

    report_text = _render_text_report(
        title=str(curriculum.get("title") or "Untitled Curriculum"),
        n_students=len(students),
        n_modules=len(modules),
        confusion_map=confusion_map,
        ordering_issues=ordering_issues,
        blooms_notes=blooms_notes,
        archetypes=archetype_perf,
        at_risk=at_risk,
    )

    overall_conf = mean([row["avg_confusion_pct"] for row in confusion_map]) if confusion_map else 0.0
    avg_retention = mean(archetype_perf.values()) if archetype_perf else 0.0
    return {
        "summary": (
            f"Insight over {len(modules)} module(s): avg confusion {overall_conf:.1f}%, "
            f"estimated retention {avg_retention:.1f}%."
        ),
        "curriculum_critique": report_text,
        "blooms_alignment_notes": blooms_notes,
        "confusion_map": confusion_map,
        "concept_ordering_issues": ordering_issues,
        "student_archetype_performance": archetype_perf,
        "at_risk_students": at_risk,
    }


def _parse_llm_json(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def _chunk_text_for_images(text: str, *, max_chars: int = _MAX_IMAGE_TEXT_CHARS) -> list[str]:
    clean = (text or "").strip()
    if not clean:
        return []
    lines = clean.splitlines()
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for line in lines:
        # keep paragraphs together when possible, but cap chunk size
        add_len = len(line) + 1
        if cur and cur_len + add_len > max_chars:
            chunks.append("\n".join(cur).strip())
            cur = [line]
            cur_len = add_len
        else:
            cur.append(line)
            cur_len += add_len
    if cur:
        chunks.append("\n".join(cur).strip())
    return [c for c in chunks if c]


def _generate_visual_report_images(
    *,
    session_id: str,
    title: str,
    critique_text: str,
) -> list[str]:
    settings = get_settings()
    if not settings.enable_visual_report:
        return []
    api_key = (settings.openai_api_key or "").strip()
    if not api_key:
        return []

    chunks = _chunk_text_for_images(critique_text)
    if not chunks:
        return []

    out_dir = settings.uploads_path / "insight_reports" / session_id
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    for idx, chunk in enumerate(chunks, start=1):
        prompt = (
            "Create an academic paper-style report page, not a slide. "
            "Use dense readable body text, clear section headers, and a professional white-paper layout "
            "(white background, black/gray text, minimal accents). "
            "Include simple line charts where quantitative trends are mentioned (for example confusion across modules, "
            "retention by module, or score trajectory). Charts must be line charts, not bars/pie. "
            "Keep charts compact (small side area) so most of the page remains text-heavy. "
            "Do not summarize, shorten, or paraphrase away details. Preserve the provided text with high fidelity. "
            "Use smaller but readable body font and tight spacing to fit more content. "
            f"Title: {title}\n"
            f"Page {idx}/{len(chunks)}\n\n"
            f"{chunk}"
        )
        payload = {
            "model": "gpt-image-2",
            "size": "1024x1536",
            "prompt": prompt,
        }
        try:
            res = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                json=payload,
                timeout=240,
            )
            if res.status_code != 200:
                logger.warning("Insight image generation failed (%s): %s", res.status_code, res.text[:500])
                continue
            body = res.json()
            data = body.get("data") if isinstance(body, dict) else None
            first = data[0] if isinstance(data, list) and data else {}
            b64 = first.get("b64_json") if isinstance(first, dict) else None
            if not isinstance(b64, str) or not b64:
                logger.warning("Insight image generation returned no b64 payload")
                continue
            out = out_dir / f"insight_{idx:02d}.png"
            out.write_bytes(base64.b64decode(b64))
            saved.append(str(out))
        except Exception as e:
            logger.warning("Insight image generation error on chunk %s: %s", idx, e)
            continue
    return saved


def _attach_visual_images_to_report(report: dict[str, Any], state: ClassroomState) -> dict[str, Any]:
    title = str(state["curriculum"].get("title") or "Curriculum Insight")
    critique = str(report.get("curriculum_critique") or "")
    paths = _generate_visual_report_images(
        session_id=str(state.get("session_id") or "session_unknown"),
        title=title,
        critique_text=critique,
    )
    if paths:
        report["visual_report_images"] = paths
    return report


def _message_content_to_str(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


def _invoke_insight_llm(user_payload: dict) -> dict[str, Any]:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_openai import ChatOpenAI

    settings = get_settings()
    body = json.dumps(user_payload, indent=2, default=str)
    messages = [
        SystemMessage(content=INSIGHT_SYSTEM_PROMPT),
        HumanMessage(content=body),
    ]

    openai_key = (settings.openai_api_key or "").strip()
    google_key = (settings.google_api_key or "").strip()

    if openai_key:
        llm = ChatOpenAI(
            model=settings.default_reasoning_model,
            api_key=openai_key,
            temperature=0.25,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
    elif google_key:
        llm = ChatGoogleGenerativeAI(
            model=settings.default_student_model,
            google_api_key=google_key,
            temperature=0.25,
        )
    else:
        raise ValueError("No LLM API key configured for insight")

    resp = llm.invoke(messages)
    return _parse_llm_json(_message_content_to_str(resp.content))


def _run_insight_llm(state: ClassroomState) -> dict:
    base_report = _build_insight_report(state)
    curriculum = state["curriculum"]
    modules = curriculum.get("modules") or []
    students = state["students"]
    module_results = sorted(state["module_results"], key=lambda r: int(r.get("module_index", -1)))

    user_payload = {
        "curriculum": {
            "title": curriculum.get("title"),
            "modules": [
                {
                    "index": i,
                    "id": m.get("id"),
                    "title": m.get("title"),
                    "content": (str(m.get("content") or "")[:1200]),
                    "blooms_level": m.get("blooms_level"),
                }
                for i, m in enumerate(modules)
            ],
        },
        "module_results": module_results,
        "students": _student_roster_for_insight(students),
        "precomputed": {
            "confusion_map": base_report.get("confusion_map"),
            "concept_ordering_issues": base_report.get("concept_ordering_issues"),
            "blooms_alignment_notes": base_report.get("blooms_alignment_notes"),
            "student_archetype_performance": base_report.get("student_archetype_performance"),
            "at_risk_students": base_report.get("at_risk_students"),
        },
    }

    parsed = _invoke_insight_llm(user_payload)
    report = {**base_report}
    if isinstance(parsed.get("summary"), str):
        report["summary"] = parsed["summary"]
    if isinstance(parsed.get("curriculum_critique"), str):
        report["curriculum_critique"] = parsed["curriculum_critique"]
    if isinstance(parsed.get("blooms_alignment_notes"), list):
        report["blooms_alignment_notes"] = parsed["blooms_alignment_notes"]
    if isinstance(parsed.get("concept_ordering_issues"), list):
        report["concept_ordering_issues"] = parsed["concept_ordering_issues"]
    if isinstance(parsed.get("recommendations"), list):
        report["llm_recommendations"] = parsed["recommendations"]
    report = _attach_visual_images_to_report(report, state)

    settings = get_settings()
    insight_backend = "openai" if (settings.openai_api_key or "").strip() else "gemini"

    return {
        "insight_report": report,
        "simulation_complete": True,
        "timestep_logs": [
            {
                "agent": "insight",
                "module_index": state["current_module"],
                "timestep": state["current_timestep"],
                "payload": {
                    "modules_analyzed": len(modules),
                    "students_analyzed": len(students),
                    "at_risk_count": len(base_report.get("at_risk_students") or []),
                    "insight_mode": "llm",
                    "insight_llm_backend": insight_backend,
                    "visual_images_count": len(report.get("visual_report_images") or []),
                },
            }
        ],
    }


def _run_insight_deterministic(state: ClassroomState) -> dict:
    curriculum = state["curriculum"]
    modules = curriculum.get("modules") or []
    students = state["students"]
    report = _build_insight_report(state)
    report = _attach_visual_images_to_report(report, state)
    at_risk = report.get("at_risk_students") or []
    return {
        "insight_report": report,
        "simulation_complete": True,
        "timestep_logs": [
            {
                "agent": "insight",
                "module_index": state["current_module"],
                "timestep": state["current_timestep"],
                "payload": {
                    "modules_analyzed": len(modules),
                    "students_analyzed": len(students),
                    "at_risk_count": len(at_risk),
                    "insight_mode": "deterministic",
                    "visual_images_count": len(report.get("visual_report_images") or []),
                },
            }
        ],
    }


def run_insight(state: ClassroomState) -> dict:
    """LLM insight when enabled and a key exists; otherwise deterministic only."""
    settings = get_settings()
    has_openai = bool((settings.openai_api_key or "").strip())
    has_google = bool((settings.google_api_key or "").strip())

    if settings.use_llm_insight and (has_openai or has_google):
        try:
            return _run_insight_llm(state)
        except Exception as e:
            logger.exception("Insight LLM failed: %s", e)
            return _run_insight_deterministic(state)
    return _run_insight_deterministic(state)


run_insight_with_llm = _run_insight_llm
run_insight_deterministic = _run_insight_deterministic
