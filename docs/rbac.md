# RBAC

MPOST has three POC roles:

```text
user
chief_of_staff
rbac_admin
```

## user

Can search documents and request persona-based recommendations.

## chief_of_staff

Can upload documents, edit metadata, and inspect ingestion status.

## rbac_admin

Can assign users to roles.

## POC Auth

The backend currently uses headers for development:

```text
X-MPOST-User-Email: chief@example.com
X-MPOST-User-Role: chief_of_staff
```

This is intentionally not production security. It exists only to make role-gated endpoints testable before adding a real identity provider.
