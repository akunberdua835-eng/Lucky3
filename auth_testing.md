# PT SJM Authentication Testing
1. Login with the admin credentials in `/app/memory/test_credentials.md`.
2. Signup a new operator account and verify the response says pending.
3. Verify the pending account cannot login.
4. From the admin session, approve the account and verify login succeeds.
5. Confirm the admin password is never rendered in the UI or API user listings.