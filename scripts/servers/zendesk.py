from mcp.server.fastmcp import FastMCP, Context
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator
from pydantic import Field
import httpx

APP_NAME = "Zendesk API"
APP_ROUTE = "zendesk"


@dataclass
class AppContext:
    base_url: str


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""
    base_url = "https://api.zendesk.com"
    try:
        yield AppContext(base_url=base_url)
    finally:
        pass


mcp = FastMCP(
    APP_NAME,
    lifespan=app_lifespan,
    sse_path=f"/{APP_ROUTE}/sse",
    message_path=f"/{APP_ROUTE}/messages/",
    debug=True,
)


@mcp.tool(name="list_tickets", description="List Tickets")
async def list_tickets(
    ctx: Context,
    external_id: str = Field(
        description="Lists tickets by external id. External ids don't have to be unique for each ticket. As a result, the request may return multiple tickets with the same external id.",
        default=None,
    ),
) -> dict:
    """List Tickets"""
    base_url = ctx.request_context.lifespan_context.base_url
    params = {"external_id": external_id}
    json = {}

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method="GET",
            url=f"{base_url}/api/v2/tickets",
            params=params,
            json=json,
        )
        return response.text


@mcp.tool(name="create_ticket", description="Create Ticket")
async def create_ticket(
    ctx: Context,
    j_additional_collaborators: str = Field(default=None),
    j_assignee_email: str = Field(default=None),
    j_assignee_id: int = Field(default=None),
    j_attribute_value_ids: str = Field(default=None),
    j_collaborator_ids: str = Field(default=None),
    j_comment: str = Field(default=None),
    j_custom_fields: str = Field(default=None),
    j_custom_status_id: int = Field(default=None),
    j_due_at: str = Field(default=None),
    j_email_ccs: str = Field(default=None),
    j_external_id: str = Field(default=None),
    j_followers: str = Field(default=None),
    j_group_id: int = Field(default=None),
    j_organization_id: int = Field(default=None),
    j_priority: str = Field(default=None),
    j_problem_id: int = Field(default=None),
    j_requester_id: int = Field(default=None),
    j_safe_update: bool = Field(default=None),
    j_sharing_agreement_ids: str = Field(default=None),
    j_status: str = Field(default=None),
    j_subject: str = Field(default=None),
    j_tags: str = Field(default=None),
    j_type: str = Field(default=None),
    j_updated_stamp: str = Field(default=None),
    j_brand_id: int = Field(default=None),
    j_collaborators: str = Field(default=None),
    j_email_cc_ids: str = Field(default=None),
    j_follower_ids: str = Field(default=None),
    j_macro_ids: str = Field(default=None),
    j_raw_subject: str = Field(default=None),
    j_recipient: str = Field(default=None),
    j_submitter_id: int = Field(default=None),
    j_ticket_form_id: int = Field(default=None),
    j_via: str = Field(default=None),
    j_via_followup_source_id: int = Field(default=None),
) -> dict:
    """Create Ticket"""
    base_url = ctx.request_context.lifespan_context.base_url
    params = {}
    json = {
        "additional_collaborators": j_additional_collaborators,
        "assignee_email": j_assignee_email,
        "assignee_id": j_assignee_id,
        "attribute_value_ids": j_attribute_value_ids,
        "collaborator_ids": j_collaborator_ids,
        "comment": j_comment,
        "custom_fields": j_custom_fields,
        "custom_status_id": j_custom_status_id,
        "due_at": j_due_at,
        "email_ccs": j_email_ccs,
        "external_id": j_external_id,
        "followers": j_followers,
        "group_id": j_group_id,
        "organization_id": j_organization_id,
        "priority": j_priority,
        "problem_id": j_problem_id,
        "requester_id": j_requester_id,
        "safe_update": j_safe_update,
        "sharing_agreement_ids": j_sharing_agreement_ids,
        "status": j_status,
        "subject": j_subject,
        "tags": j_tags,
        "type": j_type,
        "updated_stamp": j_updated_stamp,
        "brand_id": j_brand_id,
        "collaborators": j_collaborators,
        "email_cc_ids": j_email_cc_ids,
        "follower_ids": j_follower_ids,
        "macro_ids": j_macro_ids,
        "raw_subject": j_raw_subject,
        "recipient": j_recipient,
        "submitter_id": j_submitter_id,
        "ticket_form_id": j_ticket_form_id,
        "via": j_via,
        "via_followup_source_id": j_via_followup_source_id,
    }

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method="POST",
            url=f"{base_url}/api/v2/tickets",
            params=params,
            json=json,
        )
        return response.text
