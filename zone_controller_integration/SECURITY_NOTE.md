# ⚠️ SECURITY NOTICE

## Important: Revoke Your GitHub Token

Your GitHub personal access token was exposed in this conversation. **You should revoke it immediately** and create a new one if needed.

### Steps to Revoke Token

1. Go to https://github.com/settings/tokens
2. Find any tokens that were used during repository setup
3. Click "Revoke" on any tokens that were exposed
4. Create a new token if needed (Settings → Developer settings → Personal access tokens → Tokens (classic))

### Why This Matters

- Anyone with this token can access your GitHub repositories
- They can push code, create repositories, and access your account
- Always keep tokens secret and never share them in conversations

### Best Practices

- Use environment variables for tokens
- Use GitHub CLI (`gh`) with secure authentication
- Never commit tokens to git repositories
- Use fine-grained tokens with minimal permissions
- Rotate tokens regularly

## Repository Information

- **Repository**: https://github.com/ammonlee/homeassistant-smart-vent-controller
- **Status**: Successfully pushed to GitHub
- **Release**: v1.0.0 created

