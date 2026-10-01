# LAIN_OS Action Protocol — Draft 0

This document defines the first model-independent contract between planners and executors.

## Request envelope

```json
{
  "version": "0",
  "request_id": "uuid",
  "intent": "human-readable summary",
  "actions": [
    {
      "id": "a1",
      "type": "file.move",
      "arguments": {
        "source": "...",
        "destination": "..."
      }
    }
  ]
}
```

## Result envelope

```json
{
  "version": "0",
  "request_id": "uuid",
  "results": [
    {
      "action_id": "a1",
      "status": "success",
      "details": {},
      "verification": {
        "status": "passed",
        "details": {}
      }
    }
  ]
}
```

## Rules

1. Unknown action types MUST be rejected.
2. Missing required arguments MUST be rejected.
3. Executors MUST NOT reinterpret natural language.
4. Paths MUST be normalized before execution.
5. Actions MUST be bounded in time.
6. Sensitive arguments SHOULD be redacted from logs.
7. A successful process exit is not sufficient verification when a stronger postcondition exists.
8. Multi-step execution MUST stop when a required predecessor fails unless the plan explicitly defines compensating behavior.
9. Class 2 external writes MUST require explicit confirmation under the default policy.
10. An attempted external write MUST NOT be automatically retried when its outcome is ambiguous.
11. Credentials MUST NOT appear in request envelopes, results, or audit records.

## Initial capability vocabulary

### `file.copy`
Copy one local file.

### `file.move`
Move one local file.

### `file.write_text`
Create or replace a UTF-8 text file within an allowed root.

### `android.notify`
Post a local notification.

### `android.open_uri`
Launch a standards-based Android URI through an intent resolver.

### `reddit.create_post`

Create one Reddit self-post using `subreddit`, `title`, and `body` string arguments. It is a Class 2 external write, requires confirmation, and is verified through a separate post lookup. The result contains only `post_id`, `subreddit`, `permalink`, and `url`. The body is redacted from audit logs. OAuth configuration belongs outside the envelope.

ACTION_PROTOCOL intentionally exposes no general HTTP, arbitrary API, or raw Reddit capability.

## Future protocol concerns

- capability discovery;
- declared side effects;
- confirmation requirements;
- streaming progress;
- cancellation;
- rollback/compensation;
- cross-node invocation;
- authenticated envelopes;
- idempotency keys.
