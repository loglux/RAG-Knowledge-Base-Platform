#!/bin/sh
set -eu

# MCP smoke checks:
# 1) /mcp without token -> 401
# 2) /.well-known/oauth-protected-resource/mcp -> 200
# 3) Real tool-call with valid token -> success
#
# Auth options for step 3:
# - MCP_BEARER_TOKEN: use directly
# - or ADMIN_USERNAME + ADMIN_PASSWORD: login and mint short-lived MCP token

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8004}"
MCP_PATH="${MCP_PATH:-/mcp}"
MCP_URL="${MCP_URL:-${API_BASE_URL}${MCP_PATH}/}"
WELL_KNOWN_URL="${WELL_KNOWN_URL:-${API_BASE_URL}/.well-known/oauth-protected-resource/mcp}"

TMP_DIR="$(mktemp -d)"
CREATED_TOKEN_ID=""
ACCESS_TOKEN=""
MCP_TOKEN="${MCP_BEARER_TOKEN:-}"
CREATED_TEMP_TOKEN="false"

cleanup() {
  if [ "$CREATED_TEMP_TOKEN" = "true" ] && [ -n "$CREATED_TOKEN_ID" ] && [ -n "$ACCESS_TOKEN" ]; then
    curl -s -X DELETE \
      "${API_BASE_URL}/api/v1/mcp-tokens/${CREATED_TOKEN_ID}/purge" \
      -H "Authorization: Bearer ${ACCESS_TOKEN}" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT INT TERM

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[mcp-smoke] Missing required command: $1"
    exit 1
  fi
}

require_cmd curl
require_cmd python3
require_cmd docker

echo "[mcp-smoke] 1/3 Unauthorized MCP request must return 401"
CODE_401="$(curl -s -o "${TMP_DIR}/mcp_unauth.out" -w "%{http_code}" "${API_BASE_URL}${MCP_PATH}")"
if [ "$CODE_401" != "401" ]; then
  echo "[mcp-smoke] FAIL: expected 401, got ${CODE_401}"
  cat "${TMP_DIR}/mcp_unauth.out"
  exit 1
fi

echo "[mcp-smoke] 2/3 Well-known metadata must return 200"
CODE_WK="$(curl -s -o "${TMP_DIR}/well_known.out" -w "%{http_code}" "${WELL_KNOWN_URL}")"
if [ "$CODE_WK" != "200" ]; then
  echo "[mcp-smoke] FAIL: expected 200 from well-known endpoint, got ${CODE_WK}"
  cat "${TMP_DIR}/well_known.out"
  exit 1
fi

if [ -z "$MCP_TOKEN" ]; then
  if [ -z "${ADMIN_USERNAME:-}" ] || [ -z "${ADMIN_PASSWORD:-}" ]; then
    echo "[mcp-smoke] FAIL: need either MCP_BEARER_TOKEN or ADMIN_USERNAME+ADMIN_PASSWORD for authenticated tool-call"
    exit 1
  fi

  echo "[mcp-smoke] 3/3 Obtaining admin access token via /api/v1/auth/login"
  LOGIN_CODE="$(curl -s -o "${TMP_DIR}/login.json" -w "%{http_code}" \
    -X POST "${API_BASE_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${ADMIN_USERNAME}\",\"password\":\"${ADMIN_PASSWORD}\"}")"
  if [ "$LOGIN_CODE" != "200" ]; then
    echo "[mcp-smoke] FAIL: login failed with status ${LOGIN_CODE}"
    cat "${TMP_DIR}/login.json"
    exit 1
  fi

  ACCESS_TOKEN="$(python3 - <<'PY' "${TMP_DIR}/login.json"
import json, sys
data = json.load(open(sys.argv[1], "r", encoding="utf-8"))
print(data.get("access_token", ""))
PY
)"
  if [ -z "$ACCESS_TOKEN" ]; then
    echo "[mcp-smoke] FAIL: access_token missing in login response"
    exit 1
  fi

  echo "[mcp-smoke] Creating temporary MCP bearer token via /api/v1/mcp-tokens"
  CREATE_CODE="$(curl -s -o "${TMP_DIR}/mcp_token.json" -w "%{http_code}" \
    -X POST "${API_BASE_URL}/api/v1/mcp-tokens/" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"name":"mcp-smoke-temp","expires_in_days":1}')"
  if [ "$CREATE_CODE" != "200" ]; then
    echo "[mcp-smoke] FAIL: cannot create MCP token (status ${CREATE_CODE})."
    echo "[mcp-smoke] Tip: if MCP auth mode is not 'bearer', provide MCP_BEARER_TOKEN explicitly."
    cat "${TMP_DIR}/mcp_token.json"
    exit 1
  fi

  MCP_TOKEN="$(python3 - <<'PY' "${TMP_DIR}/mcp_token.json"
import json, sys
data = json.load(open(sys.argv[1], "r", encoding="utf-8"))
print(data.get("token", ""))
PY
)"
  CREATED_TOKEN_ID="$(python3 - <<'PY' "${TMP_DIR}/mcp_token.json"
import json, sys
data = json.load(open(sys.argv[1], "r", encoding="utf-8"))
record = data.get("record") or {}
print(record.get("id", ""))
PY
)"
  if [ -z "$MCP_TOKEN" ]; then
    echo "[mcp-smoke] FAIL: MCP token missing in response"
    exit 1
  fi
  CREATED_TEMP_TOKEN="true"
fi

echo "[mcp-smoke] Running authenticated MCP tool-call (list_knowledge_bases)"
docker exec \
  -e MCP_URL="$MCP_URL" \
  -e MCP_TOKEN="$MCP_TOKEN" \
  kb-platform-api \
  python - <<'PY'
import asyncio
import os
from fastmcp import Client

async def main():
    mcp_url = os.environ["MCP_URL"]
    token = os.environ["MCP_TOKEN"]
    async with Client(mcp_url, auth=token, timeout=20) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools}
        if "list_knowledge_bases" not in names:
            raise RuntimeError("list_knowledge_bases tool is missing")

        result = await client.call_tool("list_knowledge_bases", {"page": 1, "page_size": 1})
        text = str(result)
        if "knowledge base" not in text.lower() and "no knowledge bases found" not in text.lower():
            raise RuntimeError(f"unexpected tool result: {text[:300]}")

asyncio.run(main())
PY

echo "[mcp-smoke] OK"
