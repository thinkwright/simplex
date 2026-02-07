# Aftertone Documentation Standards

This document defines documentation standards for all Aftertone audio software projects.

## General Principles

Documentation should be clear, concise, and technically accurate. Avoid unnecessary embellishment or marketing language. Focus on what the code does and how to use it correctly.

## Writing Style

Write in a professional, neutral tone. Use paragraph format for explanations rather than excessive bullet points. Keep sentences direct and avoid passive voice where possible. Do not use emojis in documentation or code comments.

## Code Documentation

All public items must have documentation comments. Use triple-slash comments for items and inner doc comments for modules. Include examples where the usage is not immediately obvious.

For complex functions, document the parameters, return values, and any panics or errors that may occur. Describe the algorithm or approach if it is not standard.

## Module Documentation

Each module should have a top-level doc comment explaining its purpose and providing an overview of the types and functions it contains. Link to related modules when appropriate.

## DSP Documentation

Audio processing components require particular attention to documentation:

- Document expected input and output ranges
- Specify sample rate assumptions
- Describe any smoothing or rate-limiting applied
- For components that analyze audio/MIDI streams, document time windows and state management across buffer boundaries
- Document signal flow and processing order

## MIDI Documentation

For MIDI processing code:

- Document which MIDI message types are handled
- Specify timing considerations and latency
- Describe how state is maintained across buffer boundaries
- Document any filtering or transformation applied to events

## Examples

Examples should be complete and runnable where possible. Prefer examples that demonstrate typical usage patterns rather than edge cases. Keep examples minimal while remaining illustrative.

## Planning Documents

Planning documents (in aftertone-planning repo) follow these conventions:

- Use Markdown with clear heading hierarchy
- Include status indicators for tracked work (checkboxes, status labels)
- Keep implementation details separate from high-level roadmaps
- Update documents as work progresses

## Changelog

Maintain a changelog for significant changes. Group changes by version and categorize them as additions, changes, deprecations, removals, fixes, or security updates.
