"""Serveur MCP VoxFactura (transport stdio).

Expose les données du compte comme des outils que l'assistant IA (Claude
Desktop / Code, ou tout client MCP) appelle en langage naturel :
« mes impayés », « ma marge sur le chantier X », « ma TVA du trimestre ».

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
    """Liste les factures émises, éventuellement filtrées par statut ou chantier."""
    return _safe(
        lambda: _client().list_invoices(statut=statut, chantier_id=chantier_id, limit=limit)
    )


@mcp.tool()
def facture(facture_id: int) -> Any:
    """Détail d'une facture (lignes comprises) par son identifiant."""
    return _safe(lambda: _client().get_invoice(facture_id))


@mcp.tool()
def depenses(chantier_id: int | None = None, categorie: str | None = None) -> Any:
    """Liste les dépenses (factures de frais), filtrables par chantier ou catégorie."""
    return _safe(lambda: _client().list_expenses(chantier_id=chantier_id, categorie=categorie))


@mcp.tool()
def chantiers(statut: str | None = None) -> Any:
    """Liste les chantiers, éventuellement filtrés par statut (en_cours, termine…)."""
    return _safe(lambda: _client().list_chantiers(statut=statut))


@mcp.tool()
def clients(recherche: str | None = None) -> Any:
    """Liste les clients, avec une recherche textuelle optionnelle."""
    return _safe(lambda: _client().list_clients(search=recherche))


@mcp.tool()
def marge_chantier(chantier_id: int) -> Any:
    """Marge d'un chantier : chiffre d'affaires facturé moins les dépenses.
    Nécessite une clé avec les permissions factures + dépenses."""
    return _safe(lambda: _client().chantier_margin(chantier_id))


@mcp.tool()
def recap_tva(debut: str, fin: str) -> Any:
    """Récapitulatif TVA sur une période (dates AAAA-MM-JJ) : collectée,
    déductible, TVA nette. Nécessite la permission comptabilité."""
    return _safe(lambda: _client().vat_summary(period_start=debut, period_end=fin))


# ── Écritures (permissions dédiées ; jamais d'envoi client) ───────────────────


@mcp.tool()
def creer_devis_brouillon(
    client_id: int, lignes: list[dict], objet: str | None = None, chantier_id: int | None = None
) -> Any:
    """Crée un devis en BROUILLON (permission devis:write). Chaque ligne :
    {designation, quantite, prix_unitaire_ht, taux_tva}. Le devis n'est jamais
    envoyé automatiquement : l'artisan le relit et l'envoie dans VoxFactura."""
    return _safe(
        lambda: _client().create_devis(
            client_id=client_id, lignes=lignes, objet=objet, chantier_id=chantier_id
        )
    )


@mcp.tool()
def marquer_facture_payee(facture_id: int, montant: str | None = None) -> Any:
    """Marque une facture payée (permission payments:write). `montant` (texte,
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
    (ex. « 240.00 »). Rattache à un chantier via chantier_id."""
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
