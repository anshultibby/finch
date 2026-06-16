"""
CASParser client — Indian demat holdings via CDSL OTP fetch + CAS PDF parse.

Flow:
  1. initiate_otp(pan, bo_id, dob) → session_id  (CASParser sends OTP to user's CDSL-registered mobile)
  2. verify_otp(session_id, otp)   → list of PDF download URLs (latest eCAS)
  3. parse_cas(pdf_url, pan)        → structured holdings dict

The session_id from step 1 must be passed back by the frontend in step 2.
"""

import httpx
from typing import Optional
from core.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

CASPARSER_BASE = "https://api.casparser.in"


class CASParserError(Exception):
    pass


class CASParserClient:
    def __init__(self):
        self.api_key = Config.CASPARSER_API_KEY

    @property
    def _headers(self) -> dict:
        return {"x-api-key": self.api_key or ""}

    async def initiate_otp(self, pan: str, bo_id: str, dob: str) -> str:
        """
        Step 1: Request OTP. CDSL sends SMS to the mobile number registered with the demat account.
        Returns the session_id needed for step 2.
        Timeout is 60s because CASParser solves a CAPTCHA on the CDSL portal.
        """
        if not self.api_key:
            raise CASParserError("CASPARSER_API_KEY is not configured")

        async with httpx.AsyncClient(timeout=65.0) as client:
            resp = await client.post(
                f"{CASPARSER_BASE}/v4/cdsl/fetch",
                headers=self._headers,
                json={"pan": pan, "bo_id": bo_id, "dob": dob},
            )
            if resp.status_code != 200:
                body = resp.text
                logger.error(f"CASParser initiate_otp error {resp.status_code}: {body}")
                raise CASParserError(f"Failed to initiate OTP: {body}")
            data = resp.json()
            session_id = data.get("session_id") or data.get("id")
            if not session_id:
                raise CASParserError(f"No session_id in response: {data}")
            return session_id

    async def verify_otp(self, session_id: str, otp: str) -> list[dict]:
        """
        Step 2: Verify OTP. Returns list of {filename, url} for eCAS PDFs (up to 1 month).
        Costs 0.5 credits.
        """
        if not self.api_key:
            raise CASParserError("CASPARSER_API_KEY is not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{CASPARSER_BASE}/v4/cdsl/fetch/{session_id}/verify",
                headers=self._headers,
                json={"otp": otp, "num_periods": 1},
            )
            if resp.status_code != 200:
                body = resp.text
                logger.error(f"CASParser verify_otp error {resp.status_code}: {body}")
                if resp.status_code == 400:
                    raise CASParserError("Invalid OTP. Please try again.")
                raise CASParserError(f"OTP verification failed: {body}")
            data = resp.json()
            if isinstance(data, list):
                return data
            # Some versions wrap in a "files" key
            return data.get("files") or data.get("results") or []

    async def parse_cas(self, pdf_url: str, pan: str) -> dict:
        """
        Step 3: Parse a CAS PDF URL. Returns structured portfolio data.
        Costs 1 credit.
        """
        if not self.api_key:
            raise CASParserError("CASPARSER_API_KEY is not configured")

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{CASPARSER_BASE}/v4/smart/parse",
                headers=self._headers,
                json={"pdf_url": pdf_url, "password": pan.upper()},
            )
            if resp.status_code != 200:
                body = resp.text
                logger.error(f"CASParser parse_cas error {resp.status_code}: {body}")
                raise CASParserError(f"CAS parse failed: {body}")
            return resp.json()

    @staticmethod
    def extract_holdings(parsed: dict) -> tuple[str, list[dict], list[dict]]:
        """
        Extract investor name and demat account holdings from a parsed CAS response.
        Returns (investor_name, demat_accounts, raw_folios).

        Each demat_account:
          {dp_name, dp_id, client_id, holdings: [{isin, name, quantity, face_value}]}
        """
        investor_info = parsed.get("investor_info") or {}
        investor_name = investor_info.get("name", "")

        raw_demat = parsed.get("demat_accounts") or []
        accounts = []
        for acct in raw_demat:
            raw_holdings = acct.get("holdings") or []
            holdings = []
            for h in raw_holdings:
                qty_raw = h.get("balance") or h.get("units") or h.get("quantity") or 0
                try:
                    qty = float(qty_raw)
                except (TypeError, ValueError):
                    qty = 0.0
                fv_raw = h.get("face_value") or h.get("fv") or 0
                try:
                    fv = float(fv_raw)
                except (TypeError, ValueError):
                    fv = 0.0
                holdings.append({
                    "isin": h.get("isin", ""),
                    "name": h.get("description") or h.get("name") or h.get("security_name") or "",
                    "quantity": qty,
                    "face_value": fv,
                })
            accounts.append({
                "dp_name": acct.get("dp_name") or acct.get("depository_participant") or "",
                "dp_id": acct.get("dp_id") or acct.get("dpid") or "",
                "client_id": acct.get("client_id") or acct.get("clientid") or "",
                "holdings": holdings,
            })

        folios = parsed.get("folios") or []
        return investor_name, accounts, folios


casparser_client = CASParserClient()
