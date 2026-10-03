# voxfactura-mcp

Branche ton business **VoxFactura** sur ton assistant IA (Claude Desktop, Claude
Code, ou tout client MCP). Tu poses tes questions en langage naturel :

- « Quelles sont mes factures impayées ? »
- « Quelle est ma marge sur le chantier Villa Michu ? »
- « Combien j'ai dépensé chez Point P ce mois-ci ? »
- « Donne-moi mon récapitulatif TVA du 1er trimestre. »
- « Crée un devis brouillon pour le client 12 : 3 radiateurs à 450. »

L'assistant consulte tes données et peut préparer des **brouillons** ; il ne
**n'envoie jamais** rien à un client (l'envoi reste une validation humaine dans
VoxFactura). Tout passe par une clé API **scopée** que tu contrôles.

## 1. Crée une clé API

Dans VoxFactura : **Réglages → Clés API → Créer une clé**. Coche les permissions
voulues (lecture : factures, dépenses, chantiers, clients, comptabilité ;
écriture : créer des devis, marquer payé, ajouter des dépenses). Copie la clé
`vf_live_…` : elle n'est affichée qu'une seule fois.

- Pour la **marge chantier** : factures + dépenses.
- Pour le **récap TVA / FEC** : comptabilité.

## 2. Installe

```bash
pip install voxfactura-mcp
# ou, sans installer : uvx voxfactura-mcp
```

## 3. Configure ton client MCP

### Claude Desktop

`Réglages → Développeur → Modifier la config` :

```json
{
  "mcpServers": {
    "voxfactura": {
      "command": "voxfactura-mcp",
      "env": { "VOXFACTURA_API_KEY": "vf_live_ta_cle_ici" }
    }
  }
}
```

Redémarre Claude Desktop.

### Claude Code

```bash
claude mcp add voxfactura -e VOXFACTURA_API_KEY=vf_live_ta_cle -- voxfactura-mcp
```

## Variables d'environnement

| Variable | Rôle | Défaut |
|---|---|---|
| `VOXFACTURA_API_KEY` | Ta clé API (obligatoire) | aucune |
| `VOXFACTURA_API_BASE_URL` | URL de l'API | `https://voxfacture-production.up.railway.app` |
| `VOXFACTURA_DOSSIER` | Clé cabinet : numéro du dossier client lu par défaut | aucun |

## Cabinet comptable : une clé pour tous vos dossiers

Un cabinet d'expertise comptable crée une **clé cabinet** (`vf_cab_…`) depuis
son espace cabinet VoxFactura, page **API**. Elle lit, en lecture seule, les
dossiers des clients qui vous ont donné accès, un dossier à la fois :

- l'outil `dossiers` liste vos dossiers (numéro, raison sociale, SIREN) ;
- chaque outil accepte un paramètre `dossier` (numéro du dossier) ; à défaut,
  le serveur prend `VOXFACTURA_DOSSIER` ;
- les outils d'écriture répondent par un refus : une clé cabinet ne modifie rien ;
- chaque lecture figure dans le journal que voit votre client, qui peut retirer
  l'accès à tout moment.

```json
{
  "mcpServers": {
    "voxfactura-cabinet": {
      "command": "voxfactura-mcp",
      "env": { "VOXFACTURA_API_KEY": "vf_cab_votre_cle", "VOXFACTURA_DOSSIER": "1" }
    }
  }
}
```

## Outils

| Outil | Rôle | Permission |
|---|---|---|
| `dossiers` | Dossiers clients d'une clé cabinet | clé cabinet |
| `factures_impayees` | Factures impayées | factures |
| `factures` | Factures (filtres statut / chantier / période) | factures |
| `facture` | Détail d'une facture | factures |
| `pdf_facture` | PDF Factur-X d'une facture émise (base64) | factures |
| `depenses` | Dépenses (filtres chantier / catégorie / période) | dépenses |
| `justificatifs_depense` | Justificatifs d'une dépense | dépenses |
| `justificatif` | Fichier d'un justificatif (base64) | dépenses |
| `chantiers` | Liste des chantiers (filtres statut / client) | chantiers |
| `chantier` | Détail d'un chantier | chantiers |
| `clients` | Liste / recherche clients | clients |
| `marge_chantier` | CA facturé − dépenses d'un chantier | factures + dépenses |
| `recap_tva` | TVA collectée / déductible / nette | comptabilité |
| `journal_ventes` | Journal des ventes d'une période | comptabilité |
| `journal_achats` | Journal des achats d'une période | comptabilité |
| `journal_ventes_csv` | Journal des ventes en CSV | comptabilité |
| `journal_achats_csv` | Journal des achats en CSV | comptabilité |
| `export_fec` | Fichier des écritures comptables de l'année | comptabilité |
| `encaissements` | Factures encaissées d'une période (date, montant, moyen) | payments:read |
| `creer_devis_brouillon` | Crée un devis (brouillon) | devis:write |
| `marquer_facture_payee` | Marque une facture payée | payments:write |
| `ajouter_depense` | Ajoute une dépense | expenses:write |

Tous les outils (sauf `dossiers`) acceptent aussi `dossier`, utile seulement
avec une clé cabinet.

## API sous-jacente

Le serveur n'est qu'un habillage de l'API publique VoxFactura (lecture/écriture
scopée). Doc interactive : `https://voxfacture-production.up.railway.app/api/v1/pub/docs`.
Voir aussi [`llms.txt`](./llms.txt) et [`examples/`](./examples/).

## Licence

MIT.
