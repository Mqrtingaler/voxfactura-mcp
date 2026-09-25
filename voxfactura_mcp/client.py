"""Client HTTP de l'API publique VoxFactura (pour le serveur MCP).

Volontairement sans dépendance au reste du package (httpx + stdlib seulement),
pour être extrait tel quel dans un repo public (Phase 5). Lecture, plus des
écritures gated qui ne font jamais d'envoi client.

Identifiants : l'API publique ne parle qu'en numéros propres au compte (le
champ `id` de chaque objet et toutes les références `*_id`). Le client les
transmet tels quels, sans rien supposer d'autre.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://voxfacture-production.up.railway.app"
_TIMEOUT = 30.0


class VoxFacturaError(Exception):
    """Erreur d'appel à l'API publique VoxFactura."""


@dataclass
class VoxFacturaClient:
    """Appelle `/api/v1/pub/*` avec une clé API (Bearer)."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL

    @classmethod
    def from_env(cls) -> VoxFacturaClient:
        key = os.environ.get("VOXFACTURA_API_KEY", "").strip()
        if not key:
            raise VoxFacturaError(
                "VOXFACTURA_API_KEY manquante. Crée une clé dans Réglages -> Clés API."
            )
        base = os.environ.get("VOXFACTURA_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        return cls(api_key=key, base_url=base)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        try:
            r = httpx.get(
                f"{self.base_url}/api/v1/pub{path}",
                params=clean,
                headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
                timeout=_TIMEOUT,
            )
        except httpx.HTTPError as e:
            raise VoxFacturaError(f"appel {path} échoué : {e}") from e
        if r.status_code == 401:
            raise VoxFacturaError("Clé API invalide ou révoquée.")
        if r.status_code == 403:
            raise VoxFacturaError("Cette clé n'a pas la permission requise pour cette donnée.")
        if r.status_code >= 400:
            raise VoxFacturaError(f"{path} -> {r.status_code}: {r.text[:200]}")
        return r.json()

    def _get_text(self, path: str, params: dict[str, Any] | None = None) -> str:
        """GET d'une réponse texte (export FEC)."""
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        try:
            r = httpx.get(
                f"{self.base_url}/api/v1/pub{path}",
                params=clean,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=_TIMEOUT,
            )
        except httpx.HTTPError as e:
            raise VoxFacturaError(f"appel {path} échoué : {e}") from e
        if r.status_code == 401:
            raise VoxFacturaError("Clé API invalide ou révoquée.")
        if r.status_code == 403:
            raise VoxFacturaError("Cette clé n'a pas la permission requise pour cette donnée.")
        if r.status_code >= 400:
            raise VoxFacturaError(f"{path} -> {r.status_code}: {r.text[:200]}")
        return r.text

    def _post(self, path: str, json_body: dict[str, Any]) -> Any:
        clean = {k: v for k, v in json_body.items() if v is not None}
        try:
            r = httpx.post(
                f"{self.base_url}/api/v1/pub{path}",
                json=clean,
                headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
                timeout=_TIMEOUT,
            )
        except httpx.HTTPError as e:
            raise VoxFacturaError(f"appel {path} échoué : {e}") from e
        if r.status_code == 401:
            raise VoxFacturaError("Clé API invalide ou révoquée.")
        if r.status_code == 403:
            raise VoxFacturaError("Cette clé n'a pas la permission d'écriture requise.")
        if r.status_code >= 400:
            raise VoxFacturaError(f"{path} -> {r.status_code}: {r.text[:200]}")
        return r.json()

    # ── Lectures directes ─────────────────────────────────────────────────────
    def list_invoices(
        self,
        *,
        unpaid_only: bool = False,
        statut: str | None = None,
        chantier_id: int | None = None,
        limit: int = 50,
    ) -> list[dict]:
        page = self._get(
            "/invoices",
            {
                "unpaid_only": unpaid_only,
                "statut": statut,
                "chantier_id": chantier_id,
                "limit": limit,
            },
        )
        return page.get("data", [])

    def get_invoice(self, invoice_id: int) -> dict:
        return self._get(f"/invoices/{invoice_id}")

    def list_expenses(
        self, *, chantier_id: int | None = None, categorie: str | None = None, limit: int = 100
    ) -> list[dict]:
        page = self._get(
            "/expenses", {"chantier_id": chantier_id, "categorie": categorie, "limit": limit}
        )
        return page.get("data", [])

    def list_chantiers(
        self, *, statut: str | None = None, client_id: int | None = None, limit: int = 50
    ) -> list[dict]:
        page = self._get("/chantiers", {"statut": statut, "client_id": client_id, "limit": limit})
        return page.get("data", [])

    def get_chantier(self, chantier_id: int) -> dict:
        return self._get(f"/chantiers/{chantier_id}")

    def list_clients(self, *, search: str | None = None, limit: int = 50) -> list[dict]:
        page = self._get("/clients", {"search": search, "limit": limit})
        return page.get("data", [])

    def vat_summary(self, *, period_start: str, period_end: str) -> dict:
        return self._get(
            "/accounting/vat-summary",
            {"period_start": period_start, "period_end": period_end},
        )

    def sales_journal(self, *, period_start: str, period_end: str) -> dict:
        return self._get(
            "/accounting/sales-journal",
            {"period_start": period_start, "period_end": period_end},
        )

    def purchase_journal(self, *, period_start: str, period_end: str) -> dict:
        return self._get(
            "/accounting/purchase-journal",
            {"period_start": period_start, "period_end": period_end},
        )

    def export_fec(self, *, year: int) -> str:
        """Fichier des écritures comptables (texte tabulé) de l'année."""
        return self._get_text("/accounting/fec", {"year": year})

    # ── Écritures gated ───────────────────────────────────────────────────────
    def create_devis(
        self,
        *,
        client_id: int,
        lignes: list[dict],
        objet: str | None = None,
        chantier_id: int | None = None,
        validite_jours: int | None = None,
        date_validite: str | None = None,
        delai_execution: str | None = None,
        notes: str | None = None,
        acompte_pct: str | None = None,
    ) -> dict:
        """Crée un devis BROUILLON (jamais envoyé automatiquement). Nécessite le
        scope devis:write. `validite_jours` et `date_validite` omis : durée
        réglée sur le compte. Les champs None ne sont pas envoyés."""
        corps = {
            "client_id": client_id,
            "objet": objet,
            "chantier_id": chantier_id,
            "lignes": lignes,
            "validite_jours": validite_jours,
            "date_validite": date_validite,
            "delai_execution": delai_execution,
            "notes": notes,
            "acompte_pct": acompte_pct,
        }
        return self._post("/devis", corps)

    def mark_invoice_paid(self, invoice_id: int, *, montant: str | None = None) -> dict:
        """Marque une facture payée (payments:write). montant None -> solde total."""
        return self._post(f"/invoices/{invoice_id}/mark-paid", {"montant": montant})

    def add_expense(
        self,
        *,
        designation: str,
        montant_ttc: str,
        montant_ht: str | None = None,
        montant_tva: str | None = None,
        chantier_id: int | None = None,
        fournisseur: str | None = None,
        categorie: str | None = None,
    ) -> dict:
        """Ajoute une dépense (expenses:write)."""
        return self._post(
            "/expenses",
            {
                "designation": designation,
                "montant_ttc": montant_ttc,
                "montant_ht": montant_ht,
                "montant_tva": montant_tva,
                "chantier_id": chantier_id,
                "fournisseur": fournisseur,
                "categorie": categorie,
            },
        )

    # ── Dérivés (calcul côté client) ──────────────────────────────────────────
    def chantier_margin(self, chantier_id: int) -> dict:
        """Marge d'un chantier : CA facturé (hors annulées) - dépenses. Combine
        deux lectures (`invoices:read` + `expenses:read` requis sur la clé)."""
        invoices = self.list_invoices(chantier_id=chantier_id, limit=200)
        expenses = self.list_expenses(chantier_id=chantier_id, limit=200)
        ca_ht = sum((_dec(f.get("total_ht")) for f in invoices), Decimal("0"))
        ca_ttc = sum((_dec(f.get("total_ttc")) for f in invoices), Decimal("0"))
        dep_ht = sum((_dec(e.get("montant_ht")) for e in expenses), Decimal("0"))
        dep_ttc = sum((_dec(e.get("montant_ttc")) for e in expenses), Decimal("0"))
        marge_ht = ca_ht - dep_ht
        marge_pct = (marge_ht / ca_ht * 100) if ca_ht else Decimal("0")
        return {
            "chantier_id": chantier_id,
            "nb_factures": len(invoices),
            "nb_depenses": len(expenses),
            "ca_ht": str(ca_ht),
            "ca_ttc": str(ca_ttc),
            "depenses_ht": str(dep_ht),
            "depenses_ttc": str(dep_ttc),
            "marge_ht": str(marge_ht),
            "marge_pct": f"{marge_pct:.1f}",
        }


def _dec(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return Decimal("0")
