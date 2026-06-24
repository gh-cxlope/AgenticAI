# Google Calendar OAuth Access Token

The Google Calendar MCP example needs a temporary OAuth access token so it can read your calendar events.

For this beginner example, the fastest way to get one is Google's OAuth 2.0 Playground.

## Steps

1. Open [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground).
2. In Step 1, paste this scope into the input box:

```text
https://www.googleapis.com/auth/calendar.events
```

3. Click **Authorize APIs**.
4. Sign in with the Google account whose calendar you want to test.
5. Approve the calendar permission.
6. In Step 2, click **Exchange authorization code for tokens**.
7. Copy the **Access token** value.
8. Add it to your `.env` file:

```bash
GOOGLE_CALENDAR_OAUTH_ACCESS_TOKEN=ya29....
```

## Important

This access token is temporary. It usually expires after about 1 hour.

If `mcp_agent_production.py` works once but fails later, generate a fresh access token in the OAuth Playground and update your `.env` file.

For a real application, you would build a full OAuth flow that can refresh tokens automatically. For this learning example, the OAuth Playground token is enough.
