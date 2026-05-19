#!/usr/bin/env python3
"""
MCP Server — Google Ads (ATEA)
Stocke dans ~/Documents/googleads-mcp/
"""

import json
import asyncio
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_PATH = Path.home() / "Documents" / "googleads-mcp" / "config.json"

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def get_client():
    cfg = load_config()
    return GoogleAdsClient.load_from_dict({
        "developer_token":    cfg["developer_token"],
        "client_id":          cfg["client_id"],
        "client_secret":      cfg["client_secret"],
        "refresh_token":      cfg["refresh_token"],
        "login_customer_id":  cfg["login_customer_id"],
        "use_proto_plus":     True,
    }), cfg["customer_id"]

# ── Serveur MCP ───────────────────────────────────────────────────────────────
server = Server("googleads-atea")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_campaigns",
            description="Retourne la performance des campagnes Google Ads ATEA sur N jours",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Nombre de jours (défaut: 30)", "default": 30}
                }
            }
        ),
        Tool(
            name="get_keywords",
            description="Retourne les mots-clés avec métriques et Quality Score",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "default": 30},
                    "limit": {"type": "integer", "description": "Nombre max de mots-clés", "default": 100}
                }
            }
        ),
        Tool(
            name="get_search_terms",
            description="Retourne les termes de recherche réels des utilisateurs",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "default": 30},
                    "limit": {"type": "integer", "default": 200}
                }
            }
        ),
        Tool(
            name="get_ads",
            description="Retourne les annonces actives avec leurs métriques",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "default": 30}
                }
            }
        ),
        Tool(
            name="get_budget_overview",
            description="Vue d'ensemble des budgets et dépenses par campagne",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="pause_keyword",
            description="Met en pause un mot-clé par son ID",
            inputSchema={
                "type": "object",
                "required": ["ad_group_id", "criterion_id"],
                "properties": {
                    "ad_group_id":   {"type": "string"},
                    "criterion_id":  {"type": "string"}
                }
            }
        ),
        Tool(
            name="update_keyword_bid",
            description="Modifie l'enchère CPC max d'un mot-clé",
            inputSchema={
                "type": "object",
                "required": ["ad_group_id", "criterion_id", "cpc_bid_micros"],
                "properties": {
                    "ad_group_id":      {"type": "string"},
                    "criterion_id":     {"type": "string"},
                    "cpc_bid_micros":   {"type": "integer", "description": "Enchère en micros (ex: 1500000 = 1.50€)"}
                }
            }
        ),
        Tool(
            name="add_negative_keywords_to_campaign",
            description="Ajoute des mots-clés négatifs à une campagne spécifique",
            inputSchema={
                "type": "object",
                "required": ["campaign_id", "keywords"],
                "properties": {
                    "campaign_id": {"type": "string", "description": "ID de la campagne"},
                    "keywords":    {"type": "array", "items": {"type": "string"}, "description": "Liste de mots-clés négatifs à exclure"},
                    "match_type":  {"type": "string", "enum": ["EXACT", "PHRASE", "BROAD"], "default": "BROAD"}
                }
            }
        ),
        Tool(
            name="add_negative_keywords_to_account",
            description="Crée une liste partagée de mots-clés négatifs au niveau compte et l applique à toutes les campagnes actives",
            inputSchema={
                "type": "object",
                "required": ["list_name", "keywords"],
                "properties": {
                    "list_name":  {"type": "string", "description": "Nom de la liste partagée"},
                    "keywords":   {"type": "array", "items": {"type": "string"}, "description": "Liste de mots-clés négatifs"},
                    "match_type": {"type": "string", "enum": ["EXACT", "PHRASE", "BROAD"], "default": "BROAD"}
                }
            }
        ),
        Tool(
            name="get_negative_keywords",
            description="Retourne les mots-clés négatifs existants au niveau des campagnes",
            inputSchema={"type": "object", "properties": {}}
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        client, customer_id = get_client()
        ga = client.get_service("GoogleAdsService")
        result = {}

        # ── get_campaigns ──────────────────────────────────────────────────────
        if name == "get_campaigns":
            days = arguments.get("days", 30)
            query = f"""
                SELECT
                    campaign.id, campaign.name, campaign.status,
                    campaign.advertising_channel_type,
                    metrics.impressions, metrics.clicks,
                    metrics.cost_micros, metrics.conversions,
                    metrics.ctr, metrics.average_cpc
                FROM campaign
                WHERE segments.date DURING LAST_{days}_DAYS
                  AND campaign.status != 'REMOVED'
                ORDER BY metrics.cost_micros DESC
            """
            rows = ga.search(customer_id=customer_id, query=query)
            result = [
                {
                    "id": r.campaign.id,
                    "nom": r.campaign.name,
                    "statut": r.campaign.status.name,
                    "type": r.campaign.advertising_channel_type.name,
                    "impressions": r.metrics.impressions,
                    "clics": r.metrics.clicks,
                    "coût_€": round(r.metrics.cost_micros / 1e6, 2),
                    "conversions": round(r.metrics.conversions, 1),
                    "ctr_%": round(r.metrics.ctr * 100, 2),
                    "cpc_moy_€": round(r.metrics.average_cpc / 1e6, 2),
                }
                for r in rows
            ]

        # ── get_keywords ───────────────────────────────────────────────────────
        elif name == "get_keywords":
            days  = arguments.get("days", 30)
            limit = arguments.get("limit", 100)
            query = f"""
                SELECT
                    ad_group_criterion.criterion_id,
                    ad_group_criterion.keyword.text,
                    ad_group_criterion.keyword.match_type,
                    ad_group_criterion.status,
                    ad_group_criterion.cpc_bid_micros,
                    ad_group.id, ad_group.name,
                    campaign.name,
                    metrics.impressions, metrics.clicks,
                    metrics.cost_micros, metrics.conversions,
                    metrics.average_cpc
                FROM keyword_view
                WHERE segments.date DURING LAST_{days}_DAYS
                  AND ad_group_criterion.status != 'REMOVED'
                ORDER BY metrics.conversions DESC
                LIMIT {limit}
            """
            rows = ga.search(customer_id=customer_id, query=query)
            result = [
                {
                    "criterion_id": r.ad_group_criterion.criterion_id,
                    "ad_group_id":  r.ad_group.id,
                    "mot_clé":      r.ad_group_criterion.keyword.text,
                    "correspondance": r.ad_group_criterion.keyword.match_type.name,
                    "statut":       r.ad_group_criterion.status.name,
                    "enchère_€":    round(r.ad_group_criterion.cpc_bid_micros / 1e6, 2),
                    "campagne":     r.campaign.name,
                    "groupe":       r.ad_group.name,
                    "impressions":  r.metrics.impressions,
                    "clics":        r.metrics.clicks,
                    "coût_€":       round(r.metrics.cost_micros / 1e6, 2),
                    "conversions":  round(r.metrics.conversions, 1),
                    "cpc_moy_€":    round(r.metrics.average_cpc / 1e6, 2),
                }
                for r in rows
            ]

        # ── get_search_terms ───────────────────────────────────────────────────
        elif name == "get_search_terms":
            days  = arguments.get("days", 30)
            limit = arguments.get("limit", 200)
            query = f"""
                SELECT
                    search_term_view.search_term,
                    search_term_view.status,
                    campaign.name,
                    metrics.impressions, metrics.clicks,
                    metrics.cost_micros, metrics.conversions, metrics.ctr
                FROM search_term_view
                WHERE segments.date DURING LAST_{days}_DAYS
                ORDER BY metrics.conversions DESC
                LIMIT {limit}
            """
            rows = ga.search(customer_id=customer_id, query=query)
            result = [
                {
                    "terme":        r.search_term_view.search_term,
                    "statut":       r.search_term_view.status.name,
                    "campagne":     r.campaign.name,
                    "impressions":  r.metrics.impressions,
                    "clics":        r.metrics.clicks,
                    "coût_€":       round(r.metrics.cost_micros / 1e6, 2),
                    "conversions":  round(r.metrics.conversions, 1),
                    "ctr_%":        round(r.metrics.ctr * 100, 2),
                }
                for r in rows
            ]

        # ── get_ads ────────────────────────────────────────────────────────────
        elif name == "get_ads":
            days = arguments.get("days", 30)
            query = f"""
                SELECT
                    ad_group_ad.ad.id,
                    ad_group_ad.ad.responsive_search_ad.headlines,
                    ad_group_ad.status,
                    ad_group.name, campaign.name,
                    metrics.impressions, metrics.clicks,
                    metrics.cost_micros, metrics.conversions, metrics.ctr
                FROM ad_group_ad
                WHERE segments.date DURING LAST_{days}_DAYS
                  AND ad_group_ad.status != 'REMOVED'
                ORDER BY metrics.impressions DESC
            """
            rows = ga.search(customer_id=customer_id, query=query)
            result = [
                {
                    "id":          r.ad_group_ad.ad.id,
                    "statut":      r.ad_group_ad.status.name,
                    "campagne":    r.campaign.name,
                    "groupe":      r.ad_group.name,
                    "titres":      [h.text for h in r.ad_group_ad.ad.responsive_search_ad.headlines],
                    "impressions": r.metrics.impressions,
                    "clics":       r.metrics.clicks,
                    "coût_€":      round(r.metrics.cost_micros / 1e6, 2),
                    "conversions": round(r.metrics.conversions, 1),
                    "ctr_%":       round(r.metrics.ctr * 100, 2),
                }
                for r in rows
            ]

        # ── get_budget_overview ────────────────────────────────────────────────
        elif name == "get_budget_overview":
            query = """
                SELECT
                    campaign.name, campaign.status,
                    campaign_budget.amount_micros,
                    campaign_budget.period,
                    metrics.cost_micros
                FROM campaign
                WHERE campaign.status != 'REMOVED'
                ORDER BY campaign_budget.amount_micros DESC
            """
            rows = ga.search(customer_id=customer_id, query=query)
            result = [
                {
                    "campagne":       r.campaign.name,
                    "statut":         r.campaign.status.name,
                    "budget_jour_€":  round(r.campaign_budget.amount_micros / 1e6, 2),
                    "dépensé_total_€": round(r.metrics.cost_micros / 1e6, 2),
                }
                for r in rows
            ]

        # ── pause_keyword ──────────────────────────────────────────────────────
        elif name == "pause_keyword":
            ad_group_service = client.get_service("AdGroupCriterionService")
            op = client.get_type("AdGroupCriterionOperation")
            criterion = op.update
            criterion.resource_name = client.get_service("AdGroupCriterionService").ad_group_criterion_path(
                customer_id,
                arguments["ad_group_id"],
                arguments["criterion_id"]
            )
            criterion.status = client.enums.AdGroupCriterionStatusEnum.PAUSED
            from google.protobuf import field_mask_pb2
            op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["status"]))
            ad_group_service.mutate_ad_group_criteria(customer_id=customer_id, operations=[op])
            result = {"status": "✅ Mot-clé mis en pause avec succès"}

        # ── update_keyword_bid ─────────────────────────────────────────────────
        elif name == "update_keyword_bid":
            ad_group_service = client.get_service("AdGroupCriterionService")
            op = client.get_type("AdGroupCriterionOperation")
            criterion = op.update
            criterion.resource_name = client.get_service("AdGroupCriterionService").ad_group_criterion_path(
                customer_id,
                arguments["ad_group_id"],
                arguments["criterion_id"]
            )
            criterion.cpc_bid_micros = arguments["cpc_bid_micros"]
            from google.protobuf import field_mask_pb2
            op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["cpc_bid_micros"]))
            ad_group_service.mutate_ad_group_criteria(customer_id=customer_id, operations=[op])
            result = {"status": f"✅ Enchère mise à jour : {arguments['cpc_bid_micros'] / 1e6:.2f}€"}

        # ── add_negative_keywords_to_campaign ─────────────────────────────────
        elif name == "add_negative_keywords_to_campaign":
            campaign_service = client.get_service("CampaignCriterionService")
            match_type_enum = client.enums.KeywordMatchTypeEnum
            match_map = {"EXACT": match_type_enum.EXACT, "PHRASE": match_type_enum.PHRASE, "BROAD": match_type_enum.BROAD}
            match = match_map.get(arguments.get("match_type", "BROAD"))
            campaign_rn = client.get_service("CampaignService").campaign_path(customer_id, arguments["campaign_id"])
            operations = []
            for kw in arguments["keywords"]:
                op = client.get_type("CampaignCriterionOperation")
                criterion = op.create
                criterion.campaign = campaign_rn
                criterion.negative = True
                criterion.keyword.text = kw
                criterion.keyword.match_type = match
                operations.append(op)
            campaign_service.mutate_campaign_criteria(customer_id=customer_id, operations=operations)
            result = {"status": f"OK - {len(operations)} mots-cles negatifs ajoutes a la campagne {arguments['campaign_id']}"}

        # ── add_negative_keywords_to_account ──────────────────────────────────
        elif name == "add_negative_keywords_to_account":
            # 1. Creer la liste partagee
            shared_set_service = client.get_service("SharedSetService")
            shared_criterion_service = client.get_service("SharedCriterionService")
            campaign_shared_set_service = client.get_service("CampaignSharedSetService")

            # Creer le SharedSet
            ss_op = client.get_type("SharedSetOperation")
            ss = ss_op.create
            ss.name = arguments["list_name"]
            ss.type_ = client.enums.SharedSetTypeEnum.NEGATIVE_KEYWORDS
            ss_response = shared_set_service.mutate_shared_sets(customer_id=customer_id, operations=[ss_op])
            shared_set_rn = ss_response.results[0].resource_name

            # Ajouter les mots-cles a la liste
            match_type_enum = client.enums.KeywordMatchTypeEnum
            match_map = {"EXACT": match_type_enum.EXACT, "PHRASE": match_type_enum.PHRASE, "BROAD": match_type_enum.BROAD}
            match = match_map.get(arguments.get("match_type", "BROAD"))
            sc_ops = []
            for kw in arguments["keywords"]:
                sc_op = client.get_type("SharedCriterionOperation")
                sc = sc_op.create
                sc.shared_set = shared_set_rn
                sc.keyword.text = kw
                sc.keyword.match_type = match
                sc_ops.append(sc_op)
            shared_criterion_service.mutate_shared_criteria(customer_id=customer_id, operations=sc_ops)

            # Appliquer la liste a toutes les campagnes actives
            campaigns_query = "SELECT campaign.id, campaign.resource_name FROM campaign WHERE campaign.status = 'ENABLED'"
            campaigns = ga.search(customer_id=customer_id, query=campaigns_query)
            css_ops = []
            for camp in campaigns:
                css_op = client.get_type("CampaignSharedSetOperation")
                css = css_op.create
                css.campaign = camp.campaign.resource_name
                css.shared_set = shared_set_rn
                css_ops.append(css_op)
            if css_ops:
                campaign_shared_set_service.mutate_campaign_shared_sets(customer_id=customer_id, operations=css_ops)
            result = {"status": f"OK - Liste '{arguments['list_name']}' creee avec {len(sc_ops)} mots-cles, appliquee a {len(css_ops)} campagnes"}

        # ── get_negative_keywords ──────────────────────────────────────────────
        elif name == "get_negative_keywords":
            query = """
                SELECT campaign.name, campaign_criterion.keyword.text, campaign_criterion.keyword.match_type
                FROM campaign_criterion
                WHERE campaign_criterion.negative = TRUE
                  AND campaign_criterion.type = 'KEYWORD'
                ORDER BY campaign.name
            """
            rows = ga.search(customer_id=customer_id, query=query)
            result = [
                {
                    "campagne": r.campaign.name,
                    "mot_cle_negatif": r.campaign_criterion.keyword.text,
                    "correspondance": r.campaign_criterion.keyword.match_type.name,
                }
                for r in rows
            ]

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    except GoogleAdsException as ex:
        error_msg = f"Erreur Google Ads API: {ex.error.code().name}\n"
        for error in ex.failure.errors:
            error_msg += f"  • {error.message}\n"
        return [TextContent(type="text", text=error_msg)]
    except Exception as e:
        return [TextContent(type="text", text=f"Erreur: {str(e)}")]


# Point d'entree SSE pour Claude.ai
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Mount, Route
import uvicorn

sse = SseServerTransport("/sse/messages")

async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())

app = Starlette(routes=[
    Route("/sse", endpoint=handle_sse),
    Mount("/sse", app=sse.handle_post_message),
])

if __name__ == "__main__":
    print("Serveur MCP Google Ads demarre sur http://localhost:8080/sse")
    uvicorn.run(app, host="0.0.0.0", port=8080)
