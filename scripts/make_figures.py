#!/usr/bin/env python3
"""Génère les figures du rapport à partir des choix et mesures du projet."""
from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle

PROJECT = Path(__file__).resolve().parents[1]
FIG = PROJECT / "figures"
FIG.mkdir(exist_ok=True)
TESTS = PROJECT / "preuves" / "logs" / "tests_latest.json"

NAVY = "#10243f"
BLUE = "#2f6db3"
LIGHT = "#eaf1f9"
GREEN = "#2c7a5b"
LIGHT_GREEN = "#e6f2ec"
AMBER = "#b7791f"
LIGHT_AMBER = "#fbf1dc"
RED = "#a83232"
LIGHT_RED = "#fbe9e7"
GREY = "#5b6577"
GOLD = "#b08a3e"
INK = "#1b2433"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "text.color": INK,
    "axes.labelcolor": INK,
    "axes.edgecolor": "#c9d1de",
    "savefig.facecolor": "white",
})


def box(ax, x, y, w, h, text, fc="white", ec=BLUE, lw=1.2, fs=10, weight="normal",
        text_color=INK, radius=0.6, ls="-", align="center"):
    patch = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.02,rounding_size={radius}",
                           linewidth=lw, edgecolor=ec, facecolor=fc, linestyle=ls, zorder=3)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha=align, va="center", fontsize=fs,
            color=text_color, zorder=4, weight=weight, linespacing=1.32)
    return patch


def arrow(ax, start, end, color=GREY, lw=1.4, style="-|>", ls="-", rad=0.0, label=None,
          label_pos=0.5, fs=8.5, label_color=GREY):
    patch = FancyArrowPatch(start, end, arrowstyle=style, mutation_scale=13,
                            linewidth=lw, color=color, linestyle=ls,
                            connectionstyle=f"arc3,rad={rad}", zorder=2)
    ax.add_patch(patch)
    if label:
        mx = start[0] + (end[0] - start[0]) * label_pos
        my = start[1] + (end[1] - start[1]) * label_pos
        ax.text(mx, my + 0.8, label, ha="center", va="bottom", fontsize=fs, color=label_color,
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.92), zorder=5)


def emblem() -> None:
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.add_patch(Circle((50, 50), 45, fill=False, lw=2.6, ec=NAVY))
    ax.add_patch(Circle((50, 50), 41, fill=False, lw=0.9, ec=GOLD))
    shield = Polygon([[50, 82], [71, 73], [71, 49], [50, 26], [29, 49], [29, 73]],
                     closed=True, facecolor=NAVY, edgecolor=GOLD, lw=2.0, zorder=2)
    ax.add_patch(shield)
    ax.plot([38, 50, 62], [60, 46, 60], color=GOLD, lw=2.2, zorder=4)
    for cx in (38, 50, 62):
        ax.add_patch(Circle((cx, 60 if cx != 50 else 46), 2.3, facecolor=GOLD,
                            edgecolor=NAVY, lw=1.0, zorder=5))
    ax.plot([50, 50], [68, 61], color=GOLD, lw=1.4, zorder=4)
    ax.plot([50, 50], [42, 31], color=GOLD, lw=1.4, zorder=4)
    ax.text(50, 21, "TEK-UP", ha="center", va="center", fontsize=23, weight="bold",
            color=NAVY)
    ax.text(50, 13.5, "UNIVERSITÉ PRIVÉE · SSIR", ha="center", va="center",
            fontsize=8.2, color=GREY)
    fig.savefig(FIG / "fig_logo_tekup.png", dpi=220, transparent=True,
                bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def architecture() -> None:
    fig, ax = plt.subplots(figsize=(16, 9.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Zone 3 — flux partenaires (bandeau supérieur)
    ax.add_patch(Rectangle((2, 89.5), 96, 10, facecolor=LIGHT_RED, edgecolor=RED, lw=1.2, ls="--", zorder=0))
    ax.text(4, 96.6, "ZONE 3 — FLUX PARTENAIRES NON FIABLES", fontsize=10.5, weight="bold", color=RED)
    ax.text(4, 93.2, "Contenu importé, potentiellement hostile : jamais exécuté, toujours neutralisé avant stockage.",
            fontsize=8.6, color=GREY)
    box(ax, 73, 90.8, 23, 6.2, "Ingestion hors ligne : validation [CP3]\nneutralisation [CP4] puis étiquetage", fc="white", ec=RED, fs=8.4)

    # Zones principales
    ax.add_patch(Rectangle((2, 20), 26, 66, facecolor=LIGHT, edgecolor=BLUE, lw=1.3, zorder=0))
    ax.text(3.5, 83.3, "ZONE 0 — POSTE ANALYSTE", fontsize=10.5, weight="bold", color=BLUE)
    ax.text(3.5, 80.3, "Hôte de confiance, attesté", fontsize=8.6, color=GREY)

    ax.add_patch(Rectangle((31, 20), 41, 66, facecolor=LIGHT_GREEN, edgecolor=GREEN, lw=1.3, zorder=0))
    ax.text(32.5, 83.3, "ZONE 1 — PROCESSUS MCP (MOINDRE PRIVILÈGE)", fontsize=10.5, weight="bold", color=GREEN)
    ax.text(32.5, 80.3, "Une seule porte d'entrée, un seul journal", fontsize=8.6, color=GREY)

    ax.add_patch(Rectangle((75, 20), 23, 66, facecolor=LIGHT_AMBER, edgecolor=AMBER, lw=1.3, zorder=0))
    ax.text(76.5, 83.3, "ZONE 2 — DONNÉES CLASSIFIÉES", fontsize=10.5, weight="bold", color=AMBER)
    ax.text(76.5, 80.3, "Actifs à protéger", fontsize=8.6, color=GREY)

    # Zone 0
    box(ax, 4.5, 66, 21, 11, "Agent LLM / client MCP\n(stdio, JSON-RPC 2.0)", fc="white", ec=BLUE, fs=10)
    box(ax, 4.5, 49, 21, 11, "Jeton de capacité signé\nporté par le client\n(0600 sur l'hôte)", fc="white", ec=BLUE, fs=9.3)
    box(ax, 4.5, 32.5, 21, 11, "Attestation de posture\nEDR · chiffrement · OS\n≤ 24 h", fc="white", ec=BLUE, fs=9.3)
    box(ax, 4.5, 23.5, 21, 6, "Aucun accès direct aux données", fc=LIGHT_RED, ec=RED, fs=9.0, text_color=RED)

    # Zone 1 — chaîne de contrôle
    box(ax, 33, 69, 17.5, 11, "Authentification\nHMAC-SHA256 + posture\n[CP1]", fc="white", ec=GREEN, fs=9.2)
    box(ax, 52, 69, 17.5, 11, "Décision ABAC\nrôle · finalité · niveau\ncompartiments [CP2]", fc="white", ec=GREEN, fs=9.2)
    box(ax, 33, 53, 36.5, 10.5,
        "Six outils TI en lecture seule\nrecherche · bulletin · enrichissement · corrélation · score · santé\nschémas stricts, propriétés supplémentaires refusées [CP3]",
        fc="white", ec=GREEN, fs=8.9)
    box(ax, 33, 37, 17.5, 10.5, "Assainissement\nantiprompt-injection\n[CP4]", fc="white", ec=GREEN, fs=9.2)
    box(ax, 52, 37, 17.5, 10.5, "Enveloppe étiquetée\nétiquette · masquage\n[CP5]", fc="white", ec=GREEN, fs=9.2)
    box(ax, 33, 24.5, 17.5, 7.5, "Limiteur de débit\n[CP6]", fc="white", ec=GREEN, fs=9.2)
    box(ax, 52, 24.5, 17.5, 7.5, "Journal chaîné\npoint unique [CP7]", fc="white", ec=GREEN, fs=9.2)

    arrow(ax, (25.7, 71.5), (33, 73.5), color=BLUE, lw=1.5, style="<|-|>", label="requête / réponse\n(stdio)", label_pos=0.45, fs=7.8)
    arrow(ax, (50.7, 74.5), (52, 74.5), color=GREEN)
    arrow(ax, (60.7, 69), (60.7, 63.7), color=GREEN)
    arrow(ax, (41.7, 53), (41.7, 47.7), color=GREEN)
    arrow(ax, (50.7, 42.2), (52, 42.2), color=GREEN)
    arrow(ax, (41.7, 37), (41.7, 32.2), color=GREEN, lw=1.1, ls="--")
    arrow(ax, (60.7, 37), (60.7, 32.2), color=GREEN, lw=1.1, ls="--")
    arrow(ax, (69.7, 60.5), (77, 72), color=AMBER, lw=1.4, rad=-0.18, label="lecture filtrée\n[CP8]", label_pos=0.5, fs=7.8)

    # Zone 2
    box(ax, 77, 68, 19, 11, "SQLite TI\nouverte en lecture seule\n(0440 au repos)", fc="white", ec=AMBER, fs=9.2)
    box(ax, 77, 52, 19, 11, "Bulletins étiquetés\n0 Public → 3 Secret\ncompartiments", fc="white", ec=AMBER, fs=9.2)
    box(ax, 77, 37.5, 19, 9.5, "Clé de signature\n0400, hors base\nlue au démarrage", fc="white", ec=AMBER, fs=8.7)
    box(ax, 77, 23.5, 19, 9, "Journal d'audit\nappend-only, chaîné", fc="white", ec=AMBER, fs=9.0)
    arrow(ax, (69.7, 28.2), (77, 28), color=AMBER, lw=1.4, label="trace", label_pos=0.55, fs=7.8)

    # ingestion vers données
    arrow(ax, (84.5, 90.8), (84.5, 86.4), color=RED, lw=1.3, label="écriture maîtrisée", label_pos=0.62, fs=7.6)

    ax.text(50, 15.0, "Frontière de confiance : le client ne parle jamais aux données ; le serveur ne sort jamais du poste.",
            ha="center", fontsize=9.2, style="italic", color=NAVY)
    ax.text(50, 7.0, "Chaque flèche traversant une frontière est un point de contrôle nommé (CP1 à CP8).",
            ha="center", fontsize=8.8, color=GREY)
    fig.savefig(FIG / "fig_architecture_zones.png", dpi=200, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)


def document_path() -> None:
    fig, ax = plt.subplots(figsize=(14, 11.5))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.text(50, 97, "Parcours d'un bulletin classifié, de la source à la réponse",
            ha="center", fontsize=15, weight="bold", color=NAVY)
    ax.text(50, 93.2, "Huit étapes, un refus possible à l'étape 6, une seule trace à l'étape 8",
            ha="center", fontsize=9.8, color=GREY)

    steps = [
        ("1", "Réception partenaire", "Flux non fiable, hors ligne, quarantaine et versionnage", "ENF-05"),
        ("2", "Validation et neutralisation", "Schéma strict, taille bornée, instructions hostiles neutralisées", "EF-05 · EF-12"),
        ("3", "Étiquetage", "Niveau 0–3, TLP, compartiments de besoin d'en connaître", "EF-04"),
        ("4", "Stockage", "SQLite étiquetée, lecture seule au repos, clé hors base", "ENF-07"),
        ("5", "Demande", "initialize, jeton signé, posture du poste vérifiée", "EF-01 · EF-02"),
        ("6", "Décision", "Rôle, finalité, habilitation, compartiments", "EF-03"),
        ("7", "Enveloppe", "Étiquette de sortie, masquage des champs, canari de contrôle", "EF-04 · EF-08"),
        ("8", "Réponse et trace", "Contenu inerte livré au client, journal chaîné au point unique", "EF-08 · ENF-03"),
    ]
    top = 84.5
    step_h = 7.6
    gap = 9.2
    for index, (num, title, detail, req) in enumerate(steps):
        y = top - index * gap
        box(ax, 3, y, 60, step_h, "", fc="white", ec=GREEN if num == "6" else BLUE, lw=1.4, radius=0.8)
        ax.add_patch(Circle((7.6, y + step_h / 2), 1.85, facecolor=NAVY, edgecolor="none", zorder=5))
        ax.text(7.6, y + step_h / 2 - 0.05, num, ha="center", va="center", fontsize=9.8,
                color="white", weight="bold", zorder=6)
        ax.text(12.2, y + 5.35, title, ha="left", va="center", fontsize=10.8,
                weight="bold", color=NAVY, zorder=6)
        ax.text(12.2, y + 2.35, detail, ha="left", va="center", fontsize=8.8,
                color=INK, zorder=6)
        ax.text(60.8, y + 1.05, req, ha="right", va="center", fontsize=8.4,
                color=BLUE, weight="bold", zorder=6)
        if index < len(steps) - 1:
            arrow(ax, (7.6, y - 0.1), (7.6, y - gap + step_h + 0.1), color=GREY, lw=1.2)

    # Branche de refus à l'étape 6
    box(ax, 70, 35.5, 27, 13.5, "REFUS GÉNÉRIQUE\n« La demande ne peut pas être satisfaite… »\naucune existence révélée",
        fc=LIGHT_RED, ec=RED, fs=8.9, text_color=RED)
    arrow(ax, (63.2, 42.3), (69.8, 42.3), color=RED, lw=1.5)
    box(ax, 70, 22.0, 27, 10.5, "AUDIT SYSTÉMATIQUE\nHABILITATION_INSUFFISANTE\nou BESOIN_CONNAITRE_NON_SATISFAIT",
        fc=LIGHT_RED, ec=RED, fs=8.2, text_color=RED)
    arrow(ax, (83.5, 35.3), (83.5, 32.7), color=RED, lw=1.4)
    ax.text(70, 60.5, "Le même contenu, deux issues.\nLe refus ne dit jamais si la ressource existe.\nLes deux chemins laissent une trace.",
            fontsize=8.8, color=NAVY, va="top", linespacing=1.55)

    ax.text(50, 10.2,
            "La réponse autorisée porte son étiquette, ses mentions de manipulation et ses masques ;\n"
            "le journal conserve la décision, le motif et l'empreinte de chaque appel.",
            ha="center", fontsize=9.2, color=NAVY, linespacing=1.5)
    ax.text(50, 3.8, "Les identifiants renvoient aux exigences du dossier (EF fonctionnelles, ENF non fonctionnelles).",
            ha="center", fontsize=8.4, color=GREY)
    fig.savefig(FIG / "fig_parcours_document.png", dpi=200, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)


def risk_matrix() -> None:
    risks = [
        ("R01", "Fuite d'un bulletin Secret par réponse trop riche", 4, 5),
        ("R02", "Injection de consignes dans un flux partenaire", 4, 5),
        ("R03", "Jeton forgé, rejoué ou élevé en privilège", 3, 5),
        ("R04", "Accès hors besoin d'en connaître", 4, 4),
        ("R05", "Fuite par message d'erreur ou énumération", 4, 3),
        ("R06", "Altération ou suppression des traces", 3, 5),
        ("R07", "Poste client compromis ou non conforme", 4, 4),
        ("R08", "Saturation du service par un client", 4, 3),
        ("R09", "Empoisonnement de la base de renseignement", 3, 5),
        ("R10", "Fichiers, base ou clé laissés accessibles", 3, 4),
    ]
    fig, (ax, side) = plt.subplots(1, 2, figsize=(17, 10), gridspec_kw={"width_ratios": [1.25, 1]})
    for p in range(1, 6):
        for i in range(1, 6):
            score = p * i
            if score >= 20:
                color = "#e8b4ae"
            elif score >= 15:
                color = "#f3cfa8"
            elif score >= 9:
                color = "#f7e6ad"
            else:
                color = "#dcebd9"
            ax.add_patch(Rectangle((p - 0.5, i - 0.5), 1, 1, facecolor=color, edgecolor="white", lw=2))
            ax.text(p, i - 0.38, str(score), ha="center", va="center", fontsize=7.2, color="#7a8394")
    offsets = {
        "R01": (-0.22, 0.20), "R02": (0.22, -0.18),
        "R03": (-0.24, 0.20), "R06": (0.24, 0.20), "R09": (0.0, -0.26),
        "R04": (-0.21, 0.20), "R07": (0.21, -0.20),
        "R05": (-0.20, 0.19), "R08": (0.20, -0.19),
        "R10": (0.0, 0.0),
    }
    for rid, _, p, i in risks:
        dx, dy = offsets[rid]
        color = RED if p * i >= 20 else (AMBER if p * i >= 15 else "#5f6b7a")
        ax.add_patch(Circle((p + dx, i + dy), 0.17, facecolor="white", edgecolor=color, lw=1.9, zorder=5))
        ax.text(p + dx, i + dy, rid, ha="center", va="center", fontsize=7.3,
                weight="bold", color=color, zorder=6)
    ax.set_xlim(0.5, 5.5)
    ax.set_ylim(0.5, 5.5)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks(range(1, 6))
    ax.set_yticks(range(1, 6))
    ax.set_xticklabels(["1\nrare", "2", "3\npossible", "4\nprobable", "5\nquasi certain"], fontsize=9)
    ax.set_yticklabels(["1\nnégligeable", "2", "3\nlimité", "4\nmajeur", "5\ncritique"], fontsize=9)
    ax.set_xlabel("Probabilité (échelle 1–5)", fontsize=11, labelpad=10)
    ax.set_ylabel("Impact (échelle 1–5)", fontsize=11, labelpad=10)
    ax.set_title("Matrice probabilité × impact — score = P × I", fontsize=13, weight="bold",
                 color=NAVY, pad=16)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)

    side.axis("off")
    side.set_xlim(0, 100)
    side.set_ylim(0, 100)
    side.text(0, 97, "Risques classés", fontsize=13, weight="bold", color=NAVY)
    side.text(0, 92.8, "Le score brut départage mal les ex æquo :\nl'impact tranche, puis la probabilité.",
              fontsize=8.8, color=GREY, va="top", linespacing=1.5)
    ranked = sorted(risks, key=lambda r: (-(r[2] * r[3]), -r[3], -r[2], r[0]))
    y = 86
    for index, (rid, label, p, i) in enumerate(ranked, start=1):
        score = p * i
        color = RED if score >= 20 else (AMBER if score >= 15 else GREY)
        side.text(0, y, f"{index:02d}", fontsize=9, color=GREY, va="center")
        side.text(5.5, y, rid, fontsize=10, weight="bold", color=color, va="center")
        side.text(13.5, y, label, fontsize=9.2, color=INK, va="center")
        side.text(99.5, y, f"{score}", fontsize=10, weight="bold", color=color, va="center", ha="right")
        y -= 7.4
    side.text(0, 9.5, "Seuil de priorité P1 du score composite : 8,5 / 10.\n"
                       "Les risques R01, R02 et R07 sont ceux que la démonstration met en scène.",
              fontsize=8.4, color=GREY, va="top", linespacing=1.6)
    fig.tight_layout()
    fig.savefig(FIG / "fig_matrice_risques.png", dpi=200, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)


def comparison() -> None:
    criteria = [
        ("Sécurité du secret", 0.30, "#1f4e79"),
        ("Conformité MCP", 0.20, "#2f6db3"),
        ("Adéquation TI", 0.20, "#5b8fc9"),
        ("Maîtrise et réversibilité", 0.15, "#8fb3d9"),
        ("Coût et délai", 0.15, "#c3d6ea"),
    ]
    candidates = [
        ("C1 — Script local naïf", [0.5, 0.5, 2.0, 5.0, 5.0]),
        ("C2 — Plateforme TI commerciale", [3.5, 1.0, 4.5, 2.0, 1.5]),
        ("C3 — Passerelle MCP générique", [3.0, 4.5, 0.5, 3.5, 4.0]),
        ("C4 — Serveur MCP TI dédié (retenu)", [4.5, 4.5, 4.0, 4.5, 3.0]),
    ]
    fig, ax = plt.subplots(figsize=(16, 8.4))
    y_positions = list(range(len(candidates)))[::-1]
    for y, (name, scores) in zip(y_positions, candidates):
        left = 0.0
        total = 0.0
        for (criterion, weight, color), score in zip(criteria, scores):
            value = weight * score
            total += value
            ax.barh(y, value, left=left, height=0.52, color=color, edgecolor="white", lw=0.8)
            if value >= 0.32:
                ax.text(left + value / 2, y, f"{value:.2f}", ha="center", va="center",
                        fontsize=8.6, color="white" if color in ("#1f4e79", "#2f6db3") else INK)
            left += value
        total_label = Decimal(str(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ax.text(left + 0.06, y, f"{total_label} / 5", va="center", fontsize=11.5, weight="bold",
                color=GREEN if "retenu" in name else GREY)
    ax.set_yticks(y_positions)
    ax.set_yticklabels([name for name, _ in candidates], fontsize=10.5)
    ax.set_xlim(0, 5.5)
    ax.set_xlabel("Score pondéré (note / 5)", fontsize=11, labelpad=10)
    ax.set_title("Comparatif pondéré des quatre candidats", fontsize=14, weight="bold",
                 color=NAVY, pad=18)
    ax.grid(axis="x", color="#e3e8f0", lw=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="y", length=0)

    handles = [Rectangle((0, 0), 1, 1, color=color) for _, _, color in criteria]
    labels = [f"{name} — {int(weight * 100)} %" for name, weight, _ in criteria]
    ax.legend(handles, labels, ncol=3, frameon=False, fontsize=8.8,
              loc="upper center", bbox_to_anchor=(0.5, -0.13))
    fig.tight_layout()
    fig.savefig(FIG / "fig_comparatif.png", dpi=200, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)


def metrics() -> None:
    data = json.loads(TESTS.read_text(encoding="utf-8"))
    res = data["resume"]
    m = data["metriques"]
    lat = m["latence"]
    cards = [
        ("31 / 31", "scénarios réussis", f"{res['nominaux']} nominaux · {res['abus']} abus", GREEN),
        ("100 %", "abus maîtrisés", f"{m['abus_detectes']} / {m['abus_total']} refusés ou neutralisés", GREEN),
        (f"{lat['p95_ms']} ms", "latence p95", f"p50 {lat['p50_ms']} ms · p99 {lat['p99_ms']} ms · n={lat['n']}", BLUE),
        (f"{m['revocation']['requete_suivante_ms']} ms", "révocation appliquée", "à la requête suivante, sans redémarrage", BLUE),
        ("100 %", "audit complet", f"{m['audit']['appels_attendus']} / {m['audit']['appels_attendus']} appels · {m['audit']['entrees']} entrées", AMBER),
        ("8 → 0", "faiblesses avant / après", "maquette naïve contre serveur durci", AMBER),
    ]
    fig, ax = plt.subplots(figsize=(18, 8.6))
    ax.set_xlim(0, 3)
    ax.set_ylim(0, 2)
    ax.axis("off")
    ax.text(1.5, 1.94, "Tableau de bord de la campagne de tests",
            ha="center", fontsize=16, weight="bold", color=NAVY)
    ax.text(1.5, 1.84, "Mesures obtenues le 27 octobre 2026, laboratoire WSL2, Python 3.14.4",
            ha="center", fontsize=9.5, color=GREY)
    for index, (value, label, detail, color) in enumerate(cards):
        col = index % 3
        row = index // 3
        x = 0.03 + col * 0.985
        y = 0.98 - row * 0.87
        ax.add_patch(FancyBboxPatch((x, y), 0.94, 0.72, boxstyle="round,pad=0.01,rounding_size=0.02",
                                    facecolor="white", edgecolor="#d5deea", lw=1.4))
        ax.add_patch(Rectangle((x, y), 0.012, 0.72, facecolor=color, edgecolor="none"))
        ax.text(x + 0.06, y + 0.48, value, fontsize=27, weight="bold", color=color, va="center")
        ax.text(x + 0.06, y + 0.28, label, fontsize=12, weight="bold", color=NAVY, va="center")
        ax.text(x + 0.06, y + 0.11, detail, fontsize=9.2, color=GREY, va="center")

    inj = m["injection"]
    comp = m["comparatif_avant_apres"]
    ax.text(0.03, 0.045,
            f"Injection : {inj['malveillants_detectes']}/{inj['malveillants_total']} bulletins hostiles détectés, "
            f"{inj['faux_positifs_unitaire']} faux positif unitaire, {inj['faux_positifs_corpus']} sur le corpus bénin.    "
            f"Durcissement : uid {m['durcissement']['uid_execution']} ({m['durcissement']['utilisateur']}), "
            f"base {m['durcissement']['db_mode']}, clé {m['durcissement']['key_mode']}.",
            fontsize=8.6, color=GREY)
    fig.savefig(FIG / "fig_metriques.png", dpi=200, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)


def main() -> int:
    emblem()
    architecture()
    document_path()
    risk_matrix()
    comparison()
    metrics()
    for path in sorted(FIG.glob("fig_*.png")):
        print(f"[figure] {path.relative_to(PROJECT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
