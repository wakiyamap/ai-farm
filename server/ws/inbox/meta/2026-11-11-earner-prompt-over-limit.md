# earner cannot start: prompt over the size limit (human, 2026-11-11)

Since your 08:13Z run every earner session dies at once: "assemble-prompt: prompt for earner-local is 61377 bytes (max 60000)". The limit protects the local model context; the human raises it only as a stopgap.

Please cut what the earner gets (roles/earner.md and TOOLS.md) to leave at least 4,000 bytes of headroom: move long explanations and one-off workarounds to wiki pages and keep one line with the page name. Check the size after every edit of a role file or TOOLS.md from now on, and say the assembled size per instance in your report.
