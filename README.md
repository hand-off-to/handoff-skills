# handoff-skills

Versioned skill manifests for hand-off.to. Each skill is a system-prompt block
the agent follows when a team enables it. Mirrors the handoff-connectors
registry layout: `catalog.yaml` indexes `skills/*.yaml`, validated by
`schema/skill.schema.json`. Fetched over HTTPS (raw GitHub) or `file://`.
