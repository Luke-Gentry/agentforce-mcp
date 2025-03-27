from mcp.server.fastmcp import FastMCP, Context
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator
from pydantic import Field
import httpx

APP_NAME = "Stripe Balances"
APP_ROUTE = "stripe"


@dataclass
class AppContext:
    base_url: str


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""
    base_url = "https://api.stripe.com"
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


@mcp.tool(name="get_balance_transactions", description="List all balance transactions")
async def get_balance_transactions(
    ctx: Context,
    type: str = Field(
        description="Only returns transactions of the given type. One of: `adjustment`, `advance`, `advance_funding`, `anticipation_repayment`, `application_fee`, `application_fee_refund`, `charge`, `climate_order_purchase`, `climate_order_refund`, `connect_collection_transfer`, `contribution`, `issuing_authorization_hold`, `issuing_authorization_release`, `issuing_dispute`, `issuing_transaction`, `obligation_outbound`, `obligation_reversal_inbound`, `payment`, `payment_failure_refund`, `payment_network_reserve_hold`, `payment_network_reserve_release`, `payment_refund`, `payment_reversal`, `payment_unreconciled`, `payout`, `payout_cancel`, `payout_failure`, `payout_minimum_balance_hold`, `payout_minimum_balance_release`, `refund`, `refund_failure`, `reserve_transaction`, `reserved_funds`, `stripe_fee`, `stripe_fx_fee`, `tax_fee`, `topup`, `topup_reversal`, `transfer`, `transfer_cancel`, `transfer_failure`, or `transfer_refund`.",
        default=None,
    ),
    starting_after: str = Field(
        description="A cursor for use in pagination. `starting_after` is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, ending with `obj_foo`, your subsequent call can include `starting_after=obj_foo` in order to fetch the next page of the list.",
        default=None,
    ),
    source: str = Field(
        description="Only returns the original transaction.", default=None
    ),
    payout: str = Field(
        description="For automatic Stripe payouts only, only returns transactions that were paid out on the specified payout ID.",
        default=None,
    ),
    limit: int = Field(
        description="A limit on the number of objects to be returned. Limit can range between 1 and 100, and the default is 10.",
        default=None,
    ),
    expand: str = Field(
        description="Specifies which fields in the response should be expanded.",
        default=None,
    ),
    ending_before: str = Field(
        description="A cursor for use in pagination. `ending_before` is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, starting with `obj_bar`, your subsequent call can include `ending_before=obj_bar` in order to fetch the previous page of the list.",
        default=None,
    ),
    currency: str = Field(
        description="Only return transactions in a certain currency. Three-letter [ISO currency code](https://www.iso.org/iso-4217-currency-codes.html), in lowercase. Must be a [supported currency](https://stripe.com/docs/currencies).",
        default=None,
    ),
    created: str = Field(
        description="Only return transactions that were created during the given date interval.",
        default=None,
    ),
) -> dict:
    """List all balance transactions"""
    base_url = ctx.request_context.lifespan_context.base_url
    params = {
        "type": type,
        "starting_after": starting_after,
        "source": source,
        "payout": payout,
        "limit": limit,
        "expand": expand,
        "ending_before": ending_before,
        "currency": currency,
        "created": created,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/v1/balance_transactions", params=params
        )
        return response.json()
