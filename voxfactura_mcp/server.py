"""Serveur MCP VoxFactura (transport stdio).

Identifiants : tous les `*_id` (facture, client, chantier, prestation) sont
les numéros propres au compte (1, 2, 3...), ceux que renvoient les listes dans
leur champ `id`. Aucun identifiant interne n'est exposé ni accepté.

Expose les données du compte comme des outils que l'assistant IA (Claude
Desktop / Code, ou tout client MCP) appelle en langage naturel :
« mes impayés », « ma marge sur le chantier X », « ma TVA du trimestre ».

Comptabilité : récap TVA, journaux des ventes et des achats, export FEC.

Écritures gated (devis brouillon, marquer payé, ajouter dépense) via des
permissions dédiées ; jamais d'envoi client (ça reste une validation humaine
dans VoxFactura).

Lancement : `VOXFACTURA_API_KEY=vf_live_… voxfactura-mcp`
       ou : `VOXFACTURA_API_KEY=vf_live_… python -m voxfactura_mcp.server`
Dépendances : `mcp` + `httpx`.
"""

from __future__ import annotations

from typing import Any

from mcp.server import MCPServer

from voxfactura_mcp.client import VoxFacturaClient, VoxFacturaError

mcp = MCPServer("VoxFactura")


def _client() -> VoxFacturaClient:
    return VoxFacturaClient.from_env()


def _safe(fn: Any) -> Any:
    """Transforme une VoxFacturaError en message lisible plutôt qu'en crash
    de l'outil (meilleure UX côté assistant)."""
    try:
        return fn()
    except VoxFacturaError as e:
        return {"error": str(e)}


@mcp.tool()
def factures_impayees() -> Any:
    """Liste les factures impayées (envoyées, partiellement payées, en retard)."""
    return _safe(lambda: _client().list_invoices(unpaid_only=True))


@mcp.tool()
def factures(statut: str | None = None, chantier_id: int | None = None, limit: int = 50) -> Any:
    """Liste les factures émises, éventuellement filtrées par statut ou chantier
    (`chantier_id` = numéro du chantier dans le compte)."""
    return _safe(
        lambda: _client().list_invoices(statut=statut, chantier_id=chantier_id, limit=limit)
    )


@mcp.tool()
def facture(facture_id: int) -> Any:
    """Détail d'une facture (lignes comprises) par son numéro dans le compte
    (le champ `id` renvoyé par la liste des factures)."""
    return _safe(lambda: _client().get_invoice(facture_id))


@mcp.tool()
def depenses(chantier_id: int | None = None, categorie: str | None = None) -> Any:
    """Liste les dépenses (factures de frais), filtrables par chantier (numéro
    du chantier dans le compte) ou catégorie."""
    return _safe(lambda: _client().list_expenses(chantier_id=chantier_id, categorie=categorie))


@mcp.tool()
def chantiers(statut: str | None = None, client_id: int | None = None) -> Any:
    """Liste les chantiers, éventuellement filtrés par statut (en_cours, termine…)
    ou par client (`client_id` = numéro du client dans le compte)."""
    return _safe(lambda: _client().list_chantiers(statut=statut, client_id=client_id))


@mcp.tool()
def chantier(chantier_id: int) -> Any:
    """Détail d'un chantier par son numéro dans le compte (le champ `id`
    renvoyé par la liste des chantiers)."""
    return _safe(lambda: _client().get_chantier(chantier_id))


@mcp.tool()
def clients(recherche: str | None = None) -> Any:
    """Liste les clients, avec une recherche textuelle optionnelle."""
    return _safe(lambda: _client().list_clients(search=recherche))


@mcp.tool()
def marge_chantier(chantier_id: int) -> Any:
    """Marge d'un chantier (par son numéro dans le compte) : chiffre d'affaires
    facturé moins les dépenses. Nécessite une clé avec les permissions
    factures + dépenses."""
    return _safe(lambda: _client().chantier_margin(chantier_id))


@mcp.tool()
def recap_tva(debut: str, fin: str) -> Any:
    """Récapitulatif TVA sur une période (dates AAAA-MM-JJ) : collectée,
    déductible, TVA nette. Nécessite la permission comptabilité."""
    return _safe(lambda: _client().vat_summary(period_start=debut, period_end=fin))


@mcp.tool()
def journal_ventes(debut: str, fin: str) -> Any:
    """Journal des ventes sur une période (dates AAAA-MM-JJ) : une écriture
    par facture et avoir. Nécessite la permission comptabilité."""
    return _safe(lambda: _client().sales_journal(period_start=debut, period_end=fin))


@mcp.tool()
def journal_achats(debut: str, fin: str) -> Any:
    """Journal des achats sur une période (dates AAAA-MM-JJ) : une écriture
    par dépense. Nécessite la permission comptabilité."""
    return _safe(lambda: _client().purchase_journal(period_start=debut, period_end=fin))


@mcp.tool()
def export_fec(annee: int) -> Any:
    """Fichier des écritures comptables (FEC, texte tabulé) de l'année, à
    remettre à l'expert-comptable. Nécessite la permission comptabilité."""
    return _safe(lambda: _client().export_fec(year=annee))


# ── Écritures (permissions dédiées ; jamais d'envoi client) ───────────────────


@mcp.tool()
def creer_devis_brouillon(
    client_id: int,
    lignes: list[dict],
    objet: str | None = None,
    chantier_id: int | None = None,
    validite_jours: int | None = None,
    delai_execution: str | None = None,
    notes: str | None = None,
) -> Any:
    """Crée un devis en BROUILLON (permission devis:write). `client_id` et
    `chantier_id` sont les numéros du client et du chantier dans le compte.
    Chaque ligne : {designation, quantite, unite, prix_unitaire_ht, taux_tva},
    plus en option `prestation_id` (numéro de la prestation du catalogue) et
    `nature` (« bien » pour une vente, « service » sinon ; omise, elle suit la
    prestation du catalogue puis le réglage du compte).
    `validite_jours` : durée de validité (omis = celle réglée sur le compte,
    30 jours par défaut). `delai_execution` : délai imprimé sur le devis
    (ex. « 3 semaines après acceptation »). Le devis n'est jamais envoyé
    automatiquement : l'artisan le relit et l'envoie dans VoxFactura. Son
    `numero` est nul tant qu'il est brouillon : le numéro définitif lui est
    attribué à l'envoi."""
    return _safe(
        lambda: _client().create_devis(
            client_id=client_id,
            lignes=lignes,
            objet=objet,
            chantier_id=chantier_id,
            validite_jours=validite_jours,
            delai_execution=delai_execution,
            notes=notes,
        )
    )


@mcp.tool()
def marquer_facture_payee(facture_id: int, montant: str | None = None) -> Any:
    """Marque une facture payée (permission payments:write). `facture_id` =
    numéro de la facture dans le compte. `montant` (texte,
    ex. « 500.00 ») pour un paiement partiel ; vide = solde le total."""
    return _safe(lambda: _client().mark_invoice_paid(facture_id, montant=montant))


@mcp.tool()
def ajouter_depense(
    designation: str,
    montant_ttc: str,
    montant_ht: str | None = None,
    montant_tva: str | None = None,
    chantier_id: int | None = None,
    fournisseur: str | None = None,
    categorie: str | None = None,
) -> Any:
    """Ajoute une dépense (permission expenses:write). Montants en texte
    (ex. « 240.00 »). Rattache à un chantier via chantier_id (numéro du
    chantier dans le compte)."""
    return _safe(
        lambda: _client().add_expense(
            designation=designation,
            montant_ttc=montant_ttc,
            montant_ht=montant_ht,
            montant_tva=montant_tva,
            chantier_id=chantier_id,
            fournisseur=fournisseur,
            categorie=categorie,
        )
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
