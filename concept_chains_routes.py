"""Concept Chains: Students connect related concepts with relationships to build understanding."""

import json
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from extensions import db
from models import ConceptChain, ConceptNode, ConceptLink, ConceptChainProgress, User

concept_chains_bp = Blueprint("concept_chains", __name__)


# ---------------------------------------------------------------- helpers

def load_concept_chains_data():
    """Load all concept chains from JSON data file."""
    data_file = Path("data") / "concept_chains.json"
    if data_file.exists():
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (ValueError, OSError):
            pass
    return []


def init_concept_chains():
    """Populate database with concept chains from data file (called once at startup)."""
    if ConceptChain.query.first():
        return

    chains_data = load_concept_chains_data()
    for chain_data in chains_data:
        chain = ConceptChain(
            chain_id=chain_data["chain_id"],
            title=chain_data["title"],
            description=chain_data.get("description"),
            domain=chain_data.get("domain"),
            difficulty=chain_data.get("difficulty", "medium"),
        )
        db.session.add(chain)
        db.session.flush()

        # Add nodes
        node_map = {}
        for idx, concept in enumerate(chain_data.get("concepts", [])):
            node = ConceptNode(chain_id=chain.id, label=concept, order=idx)
            db.session.add(node)
            db.session.flush()
            node_map[concept] = node.id

        # Add correct links
        for rel in chain_data.get("relationships", []):
            from_node_id = node_map.get(rel["from"])
            to_node_id = node_map.get(rel["to"])
            if from_node_id and to_node_id:
                link = ConceptLink(
                    chain_id=chain.id,
                    from_node_id=from_node_id,
                    to_node_id=to_node_id,
                    relationship_type=rel.get("type", "relates-to"),
                )
                db.session.add(link)

    db.session.commit()


# ---------------------------------------------------------------- routes

@concept_chains_bp.route("/games")
@login_required
def games_hub():
    """Games hub for all learning games."""
    return render_template("games_hub.html")


@concept_chains_bp.route("/concept-chains")
@login_required
def list_chains():
    """List all available concept chains."""
    chains = ConceptChain.query.all()
    progress = {}

    if current_user.is_admin():
        return render_template("concept_chains_admin.html", chains=chains)

    # For students, show progress
    for chain in chains:
        prog = ConceptChainProgress.query.filter_by(
            student_id=current_user.id,
            chain_id=chain.id,
        ).first()
        progress[chain.id] = {
            "completed": prog.completed if prog else False,
            "score": prog.score_percent if prog else None,
        }

    return render_template("concept_chains_list.html", chains=chains, progress=progress)


@concept_chains_bp.route("/concept-chains/<int:chain_id>")
@login_required
def view_chain(chain_id):
    """Load a concept chain for the student to work on."""
    chain = ConceptChain.query.get_or_404(chain_id)

    # Get or create progress
    progress = ConceptChainProgress.query.filter_by(
        student_id=current_user.id,
        chain_id=chain_id,
    ).first()

    if not progress:
        progress = ConceptChainProgress(
            student_id=current_user.id,
            chain_id=chain_id,
            submitted_links="[]",
            total_possible=len(chain.correct_links),
        )
        db.session.add(progress)
        db.session.commit()

    # Prepare data for frontend
    concepts = [{"id": n.id, "label": n.label, "order": n.order} for n in chain.nodes]
    concepts.sort(key=lambda x: x["order"])

    relationship_types = set()
    for link in chain.correct_links:
        relationship_types.add(link.relationship_type)

    return render_template(
        "concept_chain_play.html",
        chain=chain,
        concepts=concepts,
        relationship_types=list(sorted(relationship_types)),
        progress=progress,
    )


@concept_chains_bp.route("/concept-chains/<int:chain_id>/submit", methods=["POST"])
@login_required
def submit_chain(chain_id):
    """Grade student's submitted concept chain."""
    chain = ConceptChain.query.get_or_404(chain_id)
    data = request.get_json()
    submitted_links = data.get("links", [])

    # Get or create progress
    progress = ConceptChainProgress.query.filter_by(
        student_id=current_user.id,
        chain_id=chain_id,
    ).first()

    if not progress:
        progress = ConceptChainProgress(
            student_id=current_user.id,
            chain_id=chain_id,
        )
        db.session.add(progress)

    # Score the submission
    correct_count = 0
    total_possible = len(chain.correct_links)

    for submitted_link in submitted_links:
        from_node_id = submitted_link.get("from")
        to_node_id = submitted_link.get("to")
        rel_type = submitted_link.get("type")

        correct_link = ConceptLink.query.filter_by(
            chain_id=chain_id,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            relationship_type=rel_type,
        ).first()

        if correct_link:
            correct_count += 1

    score_percent = (correct_count / total_possible * 100) if total_possible > 0 else 0

    progress.submitted_links = json.dumps(submitted_links)
    progress.correct_count = correct_count
    progress.total_possible = total_possible
    progress.score_percent = round(score_percent, 1)
    progress.submitted_at = datetime.utcnow()
    progress.completed = True

    db.session.commit()

    # Prepare feedback
    correct_links_data = []
    for link in chain.correct_links:
        correct_links_data.append({
            "from": link.from_node_id,
            "to": link.to_node_id,
            "type": link.relationship_type,
            "from_label": link.from_node.label,
            "to_label": link.to_node.label,
        })

    return jsonify({
        "correct_count": correct_count,
        "total_possible": total_possible,
        "score_percent": progress.score_percent,
        "correct_links": correct_links_data,
        "submitted_links": submitted_links,
    })


@concept_chains_bp.route("/concept-chains/<int:chain_id>/data")
@login_required
def get_chain_data(chain_id):
    """API endpoint to get chain data (concepts and valid relationships)."""
    chain = ConceptChain.query.get_or_404(chain_id)

    concepts = [
        {"id": n.id, "label": n.label} for n in sorted(chain.nodes, key=lambda x: x.order)
    ]

    relationship_types = list(set(
        link.relationship_type for link in chain.correct_links
    ))

    return jsonify({
        "chain_id": chain.id,
        "chain_title": chain.title,
        "concepts": concepts,
        "relationship_types": relationship_types,
    })
