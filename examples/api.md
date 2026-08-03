# Exemples d'appels à l'API publique VoxFactura

Remplace `vf_live_…` par ta clé (Réglages → Clés API).

```bash
BASE="https://voxfacture-production.up.railway.app/api/v1/pub"
KEY="vf_live_ta_cle"
AUTH="Authorization: Bearer $KEY"
```

## Lecture

```bash
# Factures impayées
curl -s -H "$AUTH" "$BASE/invoices?unpaid_only=true"

# Détail d'une facture (avec lignes)
curl -s -H "$AUTH" "$BASE/invoices/1"

# Dépenses d'un chantier
curl -s -H "$AUTH" "$BASE/expenses?chantier_id=42"

# Chantiers en cours
curl -s -H "$AUTH" "$BASE/chantiers?statut=en_cours"

# Récapitulatif TVA du 1er trimestre 2026
curl -s -H "$AUTH" "$BASE/accounting/vat-summary?period_start=2026-01-01&period_end=2026-03-31"

# Export FEC 2026 (téléchargement)
curl -s -H "$AUTH" "$BASE/accounting/fec?year=2026" -o FEC_2026.txt
```

## Écriture (permissions dédiées ; jamais d'envoi client)

```bash
# Créer un devis brouillon
curl -s -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"client_id":3,"objet":"Toiture","lignes":[
        {"designation":"Radiateur","quantite":3,"prix_unitaire_ht":450,"taux_tva":10}]}' \
  "$BASE/devis"

# Marquer une facture payée (partiel possible via montant)
curl -s -H "$AUTH" -H "Content-Type: application/json" \
  -d '{}' "$BASE/invoices/1/mark-paid"

# Ajouter une dépense rattachée à un chantier
curl -s -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"designation":"Ciment","montant_ttc":"240.00","categorie":"materiel","chantier_id":42}' \
  "$BASE/expenses"
```

## Python (client fourni)

```python
from voxfactura_mcp.client import VoxFacturaClient

c = VoxFacturaClient(api_key="vf_live_ta_cle")
print(c.list_invoices(unpaid_only=True))
print(c.chantier_margin(42))
```
